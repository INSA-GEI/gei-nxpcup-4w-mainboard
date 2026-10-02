"""
mcx_i2c.py

Bibliothèque de communication I2C avec le microcontrôleur MCXA153
("carte Gemini") depuis un hôte Linux (ex: NXP FRDM-IMX8MPLUS).

Le MCU simule un capteur/actionneur exposant une carte de registres 8 bits
(voir `Register`). Le protocole bas niveau, imposé par le firmware esclave
(`i2c_slave_gemini.c`), est le suivant :

  - Écriture : le maître envoie [index_registre, data0, data1, ...].
    Le premier octet transmis est toujours l'index du registre visé.
    Les octets suivants sont écrits dans les registres consécutifs
    (auto-incrément côté esclave), mais seuls les registres RW
    (MOT1 à CR) sont effectivement modifiés ; une écriture sur un
    registre RO est silencieusement ignorée par le MCU.

  - Lecture : le maître envoie l'index du registre de départ (sans STOP),
    puis lit N octets consécutifs ; l'esclave incrémente son propre
    pointeur après chaque octet transmis.

Ce protocole correspond exactement à une transaction "I2C block"
(write pointeur + repeated start + read bloc, SANS octet de taille en
tête de la réponse), ce qui est directement pris en charge par
`smbus2.SMBus.read_i2c_block_data` / `write_i2c_block_data`.

Dépendance : smbus2 (`pip install smbus2`), Linux uniquement.
"""

from __future__ import annotations

import struct
import threading
from dataclasses import dataclass
from enum import IntEnum
from types import TracebackType
from typing import List, Optional, Type

try:
    from smbus2 import SMBus
except ImportError as exc:  # pragma: no cover - message d'aide au premier lancement
    raise ImportError(
        "Le module 'smbus2' est requis pour utiliser mcx_i2c.\n"
        "Installez-le avec : pip install smbus2"
    ) from exc


# ---------------------------------------------------------------------------
# Constantes issues du firmware (configuration.h / i2c_slave_gemini.h)
# ---------------------------------------------------------------------------

I2C_SLAVE_ADDRESS = 0x42
"""Adresse I2C 7 bits du microcontrôleur esclave (I2C_SLAVE_ADDR)."""

BOARD_ID = 0x10
"""Valeur attendue du registre REG_ID (identifiant fixe de la carte)."""


class Register(IntEnum):
    """Index des registres exposés par le microcontrôleur (i2c_reg_index_t)."""

    ID = 0x00       # RO - Identifiant carte (toujours 0x10)
    VER = 0x01      # RO - Version du firmware
    VBAT_1R = 0x02  # RO - Tension batterie, octet LSB (mV, uint16 LE)
    VBAT_2R = 0x03  # RO - Tension batterie, octet MSB
    ODO1_1R = 0x04  # RO - Odomètre 1, octet 0 (LSB, uint32 LE)
    ODO1_2R = 0x05  # RO - Odomètre 1, octet 1
    ODO1_3R = 0x06  # RO - Odomètre 1, octet 2
    ODO1_4R = 0x07  # RO - Odomètre 1, octet 3 (MSB)
    ODO2_1R = 0x08  # RO - Odomètre 2, octet 0 (LSB, uint32 LE)
    ODO2_2R = 0x09  # RO - Odomètre 2, octet 1
    ODO2_3R = 0x0A  # RO - Odomètre 2, octet 2
    ODO2_4R = 0x0B  # RO - Odomètre 2, octet 3 (MSB)
    MOT1 = 0x0C     # RW - Moteur 1 (gauche), duty cycle 0-100 (%)
    MOT2 = 0x0D     # RW - Moteur 2 (droit), duty cycle 0-100 (%)
    DIR = 0x0E      # RW - Direction servo, int8 signé -100..100
    CR = 0x0F       # RW - Registre de contrôle / status système


REG_MAX_IDX = Register.CR
REG_COUNT = REG_MAX_IDX + 1  # nombre total de registres (0x00 à 0x0F inclus)

# Registres accessibles en écriture par le maître (is_rw_register côté firmware)
_RW_REGISTERS = frozenset(
    r for r in Register if Register.MOT1 <= r <= Register.CR
)


class ControlBit(IntEnum):
    """
    Bits proposés pour le registre de contrôle REG_CR.

    ATTENTION : le firmware fourni définit REG_CR comme un simple registre
    de contrôle RW générique, sans affecter explicitement la signification
    de chaque bit dans les sources transmises. Les bits ci-dessous sont une
    convention par défaut à adapter à l'implémentation réelle côté MCU
    (notamment pour la gestion de la demande d'arrêt du système) :

      - SHUTDOWN_REQUEST : mis à 1 par le MCU pour signaler à l'hôte Linux
        qu'un arrêt du système est demandé (ex: bouton poussoir, batterie
        faible).
      - SHUTDOWN_ACK : à mettre à 1 par l'hôte pour accuser réception de la
        demande avant de s'éteindre, si ce mécanisme est implémenté côté MCU.
    """

    SHUTDOWN_REQUEST = 0
    SHUTDOWN_ACK = 1


class MCXBoardError(Exception):
    """Erreur de communication avec la carte MCX (I2C indisponible, etc.)."""


@dataclass
class BoardStatus:
    """Instantané complet de l'état de la carte (une lecture bloc de 16 octets)."""

    board_id: int
    firmware_version: int
    vbat_mv: int
    odometer1: int
    odometer2: int
    motor1: int
    motor2: int
    direction: int
    control_register: int

    def __str__(self) -> str:  # pragma: no cover - confort d'affichage
        return (
            f"ID=0x{self.board_id:02X} FW=v{self.firmware_version} "
            f"VBAT={self.vbat_mv} mV | "
            f"ODO1={self.odometer1} ODO2={self.odometer2} | "
            f"MOT1={self.motor1}% MOT2={self.motor2}% DIR={self.direction} | "
            f"CR=0x{self.control_register:02X}"
        )


def _to_int8(byte_value: int) -> int:
    """Convertit un octet non signé (0-255) en entier signé 8 bits."""
    return struct.unpack("<b", bytes([byte_value & 0xFF]))[0]


def _from_int8(value: int) -> int:
    """Convertit un entier signé 8 bits (-128..127) en octet non signé."""
    if not -128 <= value <= 127:
        raise ValueError(f"Valeur {value} hors plage int8 (-128..127)")
    return struct.pack("<b", value)[0]


class MCXBoard:
    """
    Encapsule la communication I2C avec le microcontrôleur MCXA153.

    Exemple :
        with MCXBoard(bus=2) as board:
            print(board.get_status())
            board.set_motors(30, 30)
            board.set_direction(0)
    """

    def __init__(
        self,
        bus: int = 2,
        address: int = I2C_SLAVE_ADDRESS,
        auto_open: bool = True,
    ) -> None:
        """
        Args:
            bus: numéro du bus I2C Linux (ex: 2 pour /dev/i2c-2). Utilisez
                `i2cdetect -l` sur la carte FRDM-IMX8MPLUS pour identifier
                le bus correspondant à I2C2.
            address: adresse I2C 7 bits du microcontrôleur esclave.
            auto_open: ouvre immédiatement le bus si True (par défaut).
        """
        self._bus_number = bus
        self._address = address
        self._bus: Optional[SMBus] = None
        self._lock = threading.Lock()
        if auto_open:
            self.open()

    # -- Gestion du cycle de vie -------------------------------------------------

    def open(self) -> None:
        """Ouvre le bus I2C. Sans effet si déjà ouvert."""
        if self._bus is None:
            try:
                self._bus = SMBus(self._bus_number)
            except (FileNotFoundError, OSError) as exc:
                raise MCXBoardError(
                    f"Impossible d'ouvrir /dev/i2c-{self._bus_number} : {exc}"
                ) from exc

    def close(self) -> None:
        """Ferme le bus I2C. Sans effet si déjà fermé."""
        if self._bus is not None:
            self._bus.close()
            self._bus = None

    def __enter__(self) -> "MCXBoard":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - filet de sécurité
        try:
            self.close()
        except Exception:
            pass

    # -- Accès bas niveau ---------------------------------------------------

    def _read_raw(self, start_reg: Register, length: int) -> List[int]:
        """Lit `length` octets consécutifs à partir de `start_reg`."""
        if self._bus is None:
            raise MCXBoardError("Bus I2C non ouvert (appelez open() ou utilisez 'with')")
        if start_reg + length - 1 > REG_MAX_IDX:
            raise ValueError("Lecture débordant de la carte de registres")
        with self._lock:
            try:
                return self._bus.read_i2c_block_data(self._address, int(start_reg), length)
            except OSError as exc:
                raise MCXBoardError(
                    f"Échec de lecture I2C (reg=0x{start_reg:02X}, len={length}) : {exc}"
                ) from exc

    def _write_raw(self, start_reg: Register, data: List[int]) -> None:
        """Écrit les octets de `data` à partir de `start_reg` (registres RW uniquement)."""
        if self._bus is None:
            raise MCXBoardError("Bus I2C non ouvert (appelez open() ou utilisez 'with')")
        if start_reg + len(data) - 1 > REG_MAX_IDX:
            raise ValueError("Écriture débordant de la carte de registres")
        with self._lock:
            try:
                self._bus.write_i2c_block_data(self._address, int(start_reg), data)
            except OSError as exc:
                raise MCXBoardError(
                    f"Échec d'écriture I2C (reg=0x{start_reg:02X}, len={len(data)}) : {exc}"
                ) from exc

    def read_register(self, reg: Register) -> int:
        """Lit un seul registre et retourne sa valeur brute (0-255)."""
        return self._read_raw(reg, 1)[0]

    def write_register(self, reg: Register, value: int) -> None:
        """
        Écrit un seul registre.

        Note : le MCU ignore silencieusement l'écriture si `reg` n'est pas
        un registre RW (ID, VER, VBAT_*, ODO*_*).
        """
        if not 0 <= value <= 255:
            raise ValueError("La valeur d'un registre doit être comprise entre 0 et 255")
        if reg not in _RW_REGISTERS:
            raise MCXBoardError(
                f"Le registre {reg.name} est en lecture seule (RO) côté firmware"
            )
        self._write_raw(reg, [value])

    # -- Registres d'identification -----------------------------------------

    def get_id(self) -> int:
        """Retourne l'identifiant de la carte (constant, doit valoir BOARD_ID)."""
        return self.read_register(Register.ID)

    def get_firmware_version(self) -> int:
        """Retourne la version du firmware du MCU."""
        return self.read_register(Register.VER)

    def is_board_present(self) -> bool:
        """Vérifie que le microcontrôleur répond et renvoie un ID cohérent."""
        try:
            return self.get_id() == BOARD_ID
        except MCXBoardError:
            return False

    # -- Batterie -------------------------------------------------------------

    def get_vbat_mv(self) -> int:
        """Retourne la tension batterie en millivolts (uint16)."""
        raw = self._read_raw(Register.VBAT_1R, 2)
        return struct.unpack("<H", bytes(raw))[0]

    # -- Odomètres --------------------------------------------------------------

    def get_odometer(self, index: int) -> int:
        """Retourne la valeur brute (uint32, nombre d'impulsions) de l'odomètre 1 ou 2."""
        if index == 1:
            start = Register.ODO1_1R
        elif index == 2:
            start = Register.ODO2_1R
        else:
            raise ValueError("index odomètre invalide (attendu : 1 ou 2)")
        raw = self._read_raw(start, 4)
        return struct.unpack("<I", bytes(raw))[0]

    def get_odometers(self) -> tuple[int, int]:
        """Retourne (odomètre1, odomètre2) en une seule transaction I2C."""
        raw = self._read_raw(Register.ODO1_1R, 8)
        odo1, odo2 = struct.unpack("<II", bytes(raw))
        return odo1, odo2

    # -- Moteurs ----------------------------------------------------------------

    def get_motor(self, index: int) -> int:
        """Retourne le duty cycle courant (0-100 %) du moteur 1 ou 2."""
        reg = self._motor_register(index)
        return self.read_register(reg)

    def set_motor(self, index: int, duty_cycle: int) -> None:
        """Règle le duty cycle (0-100 %) du moteur 1 ou 2."""
        if not 0 <= duty_cycle <= 100:
            raise ValueError("Le duty cycle moteur doit être compris entre 0 et 100")
        reg = self._motor_register(index)
        self.write_register(reg, duty_cycle)

    def set_motors(self, duty_left: int, duty_right: int) -> None:
        """Règle simultanément les deux moteurs en une seule transaction I2C."""
        if not (0 <= duty_left <= 100 and 0 <= duty_right <= 100):
            raise ValueError("Les duty cycles moteurs doivent être compris entre 0 et 100")
        self._write_raw(Register.MOT1, [duty_left, duty_right])

    @staticmethod
    def _motor_register(index: int) -> Register:
        if index == 1:
            return Register.MOT1
        if index == 2:
            return Register.MOT2
        raise ValueError("index moteur invalide (attendu : 1 ou 2)")

    # -- Direction (servo) --------------------------------------------------

    def get_direction(self) -> int:
        """Retourne la direction courante du servo, en pourcentage signé (-100..100)."""
        raw = self.read_register(Register.DIR)
        return _to_int8(raw)

    def set_direction(self, value: int) -> None:
        """Règle la direction du servo, en pourcentage signé (-100..100)."""
        if not -100 <= value <= 100:
            raise ValueError("La direction doit être comprise entre -100 et 100")
        self._write_raw(Register.DIR, [_from_int8(value)])

    def set_motors_and_direction(self, duty_left: int, duty_right: int, direction: int) -> None:
        """Règle moteurs + direction en une seule transaction I2C (MOT1, MOT2, DIR consécutifs)."""
        if not (0 <= duty_left <= 100 and 0 <= duty_right <= 100):
            raise ValueError("Les duty cycles moteurs doivent être compris entre 0 et 100")
        if not -100 <= direction <= 100:
            raise ValueError("La direction doit être comprise entre -100 et 100")
        self._write_raw(Register.MOT1, [duty_left, duty_right, _from_int8(direction)])

    # -- Registre de contrôle / status ---------------------------------------

    def get_control_register(self) -> int:
        """Retourne la valeur brute du registre de contrôle (REG_CR)."""
        return self.read_register(Register.CR)

    def set_control_register(self, value: int) -> None:
        """Écrit une valeur brute dans le registre de contrôle (REG_CR)."""
        self.write_register(Register.CR, value)

    def get_control_bit(self, bit: ControlBit | int) -> bool:
        """Lit un bit individuel du registre de contrôle."""
        return bool(self.get_control_register() & (1 << int(bit)))

    def set_control_bit(self, bit: ControlBit | int, value: bool = True) -> None:
        """Positionne (ou efface) un bit individuel du registre de contrôle (read-modify-write)."""
        current = self.get_control_register()
        if value:
            new_value = current | (1 << int(bit))
        else:
            new_value = current & ~(1 << int(bit))
        self.set_control_register(new_value & 0xFF)

    def is_shutdown_requested(self) -> bool:
        """Indique si le MCU a positionné le bit de demande d'arrêt (convention ControlBit)."""
        return self.get_control_bit(ControlBit.SHUTDOWN_REQUEST)

    def acknowledge_shutdown(self) -> None:
        """Positionne le bit d'accusé de réception de la demande d'arrêt (convention ControlBit)."""
        self.set_control_bit(ControlBit.SHUTDOWN_ACK, True)

    # -- Lecture globale ------------------------------------------------------

    def get_status(self) -> BoardStatus:
        """Lit l'intégralité de la carte de registres (0x00-0x0F) en une seule transaction I2C."""
        raw = self._read_raw(Register.ID, REG_COUNT)
        board_id, fw_version = raw[0], raw[1]
        vbat_mv = struct.unpack("<H", bytes(raw[2:4]))[0]
        odo1, odo2 = struct.unpack("<II", bytes(raw[4:12]))
        motor1, motor2 = raw[12], raw[13]
        direction = _to_int8(raw[14])
        control_register = raw[15]
        return BoardStatus(
            board_id=board_id,
            firmware_version=fw_version,
            vbat_mv=vbat_mv,
            odometer1=odo1,
            odometer2=odo2,
            motor1=motor1,
            motor2=motor2,
            direction=direction,
            control_register=control_register,
        )
