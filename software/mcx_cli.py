#!/usr/bin/env python3
"""
mcx_cli.py

Application CLI d'exemple pour piloter/superviser la carte MCXA153 via I2C,
en s'appuyant sur la bibliothèque mcx_i2c.

Exemples d'utilisation :

    # Afficher un instantané complet de la carte (bus I2C2 = /dev/i2c-2)
    ./mcx_cli.py --bus 2 status

    # Surveiller la carte en continu (rafraîchi toutes les 0.5 s)
    ./mcx_cli.py --bus 2 status --watch --interval 0.5

    # Lire la tension batterie
    ./mcx_cli.py --bus 2 vbat

    # Lire les odomètres
    ./mcx_cli.py --bus 2 odometer

    # Commander les deux moteurs et la direction en une transaction
    ./mcx_cli.py --bus 2 drive 40 40 0

    # Régler un seul moteur
    ./mcx_cli.py --bus 2 motor set 1 25

    # Lire/écrire le registre de contrôle (arrêt système, etc.)
    ./mcx_cli.py --bus 2 cr get
    ./mcx_cli.py --bus 2 cr set 0x00
    ./mcx_cli.py --bus 2 cr ack-shutdown
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

from mcx_i2c import (
    BOARD_ID,
    ControlBit,
    I2C_SLAVE_ADDRESS,
    MCXBoard,
    MCXBoardError,
)


def _auto_int(value: str) -> int:
    """Permet de saisir un entier en décimal (100) ou en hexadécimal (0x64)."""
    return int(value, 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcx_cli.py",
        description="Client CLI pour la carte MCXA153 (bus I2C esclave).",
    )
    parser.add_argument(
        "--bus", type=int, default=2,
        help="Numéro du bus I2C Linux (/dev/i2c-N). Défaut : 2.",
    )
    parser.add_argument(
        "--address", type=_auto_int, default=I2C_SLAVE_ADDRESS,
        help=f"Adresse I2C 7 bits du MCU. Défaut : 0x{I2C_SLAVE_ADDRESS:02X}.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = sub.add_parser("status", help="Affiche un instantané complet de la carte")
    p_status.add_argument("--watch", action="store_true", help="Rafraîchit en continu (Ctrl+C pour arrêter)")
    p_status.add_argument("--interval", type=float, default=1.0, help="Intervalle de rafraîchissement en secondes")

    # vbat
    sub.add_parser("vbat", help="Affiche la tension batterie (mV)")

    # odometer
    p_odo = sub.add_parser("odometer", help="Affiche la valeur des odomètres")
    p_odo.add_argument("index", type=int, nargs="?", choices=[1, 2], help="Odomètre 1 ou 2 (les deux si omis)")

    # motor
    p_motor = sub.add_parser("motor", help="Lit ou règle un moteur")
    motor_sub = p_motor.add_subparsers(dest="motor_action", required=True)
    p_motor_get = motor_sub.add_parser("get", help="Lit le duty cycle courant")
    p_motor_get.add_argument("index", type=int, choices=[1, 2])
    p_motor_set = motor_sub.add_parser("set", help="Règle le duty cycle (0-100)")
    p_motor_set.add_argument("index", type=int, choices=[1, 2])
    p_motor_set.add_argument("duty_cycle", type=int)

    # direction
    p_dir = sub.add_parser("direction", help="Lit ou règle la direction du servo")
    dir_sub = p_dir.add_subparsers(dest="direction_action", required=True)
    dir_sub.add_parser("get", help="Lit la direction courante")
    p_dir_set = dir_sub.add_parser("set", help="Règle la direction (-100 à 100)")
    p_dir_set.add_argument("value", type=int)

    # drive (moteurs + direction en une transaction)
    p_drive = sub.add_parser("drive", help="Règle moteur gauche, moteur droit et direction en une transaction")
    p_drive.add_argument("duty_left", type=int, help="Duty cycle moteur gauche (0-100)")
    p_drive.add_argument("duty_right", type=int, help="Duty cycle moteur droit (0-100)")
    p_drive.add_argument("direction", type=int, help="Direction du servo (-100 à 100)")

    # stop (arrêt d'urgence : moteurs à 0, direction neutre)
    sub.add_parser("stop", help="Arrête les moteurs et recentre la direction")

    # control register (CR)
    p_cr = sub.add_parser("cr", help="Lit ou écrit le registre de contrôle (REG_CR)")
    cr_sub = p_cr.add_subparsers(dest="cr_action", required=True)
    cr_sub.add_parser("get", help="Lit la valeur brute du registre de contrôle")
    p_cr_set = cr_sub.add_parser("set", help="Écrit une valeur brute (0-255, décimal ou 0x..)")
    p_cr_set.add_argument("value", type=_auto_int)
    cr_sub.add_parser("shutdown-requested", help="Indique si le MCU demande l'arrêt du système")
    cr_sub.add_parser("ack-shutdown", help="Positionne le bit d'accusé de réception d'arrêt")

    # info
    sub.add_parser("info", help="Affiche l'identifiant et la version firmware de la carte")

    return parser


def cmd_status(board: MCXBoard, args: argparse.Namespace) -> None:
    def _print_once() -> None:
        status = board.get_status()
        print(status)

    if not args.watch:
        _print_once()
        return

    try:
        while True:
            _print_once()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print()  # nouvelle ligne propre après ^C


def cmd_vbat(board: MCXBoard) -> None:
    print(f"VBAT = {board.get_vbat_mv()} mV")


def cmd_odometer(board: MCXBoard, index: Optional[int]) -> None:
    if index is None:
        odo1, odo2 = board.get_odometers()
        print(f"Odomètre 1 = {odo1}")
        print(f"Odomètre 2 = {odo2}")
    else:
        print(f"Odomètre {index} = {board.get_odometer(index)}")


def cmd_motor(board: MCXBoard, args: argparse.Namespace) -> None:
    if args.motor_action == "get":
        print(f"Moteur {args.index} = {board.get_motor(args.index)} %")
    elif args.motor_action == "set":
        board.set_motor(args.index, args.duty_cycle)
        print(f"Moteur {args.index} réglé à {args.duty_cycle} %")


def cmd_direction(board: MCXBoard, args: argparse.Namespace) -> None:
    if args.direction_action == "get":
        print(f"Direction = {board.get_direction()}")
    elif args.direction_action == "set":
        board.set_direction(args.value)
        print(f"Direction réglée à {args.value}")


def cmd_drive(board: MCXBoard, args: argparse.Namespace) -> None:
    board.set_motors_and_direction(args.duty_left, args.duty_right, args.direction)
    print(
        f"MOT1={args.duty_left}%  MOT2={args.duty_right}%  DIR={args.direction} -> envoyés"
    )


def cmd_stop(board: MCXBoard) -> None:
    board.set_motors_and_direction(0, 0, 0)
    print("Moteurs arrêtés, direction recentrée")


def cmd_cr(board: MCXBoard, args: argparse.Namespace) -> None:
    if args.cr_action == "get":
        value = board.get_control_register()
        print(f"CR = 0x{value:02X} ({value})")
    elif args.cr_action == "set":
        if not 0 <= args.value <= 255:
            print("Erreur : la valeur doit être comprise entre 0 et 255", file=sys.stderr)
            sys.exit(1)
        board.set_control_register(args.value)
        print(f"CR réglé à 0x{args.value:02X}")
    elif args.cr_action == "shutdown-requested":
        print("Oui" if board.is_shutdown_requested() else "Non")
    elif args.cr_action == "ack-shutdown":
        board.acknowledge_shutdown()
        print("Bit d'accusé de réception d'arrêt positionné")


def cmd_info(board: MCXBoard) -> None:
    board_id = board.get_id()
    fw_version = board.get_firmware_version()
    match = "OK" if board_id == BOARD_ID else "INATTENDU"
    print(f"ID carte       : 0x{board_id:02X} ({match})")
    print(f"Version FW     : {fw_version}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        with MCXBoard(bus=args.bus, address=args.address) as board:
            if args.command == "status":
                cmd_status(board, args)
            elif args.command == "vbat":
                cmd_vbat(board)
            elif args.command == "odometer":
                cmd_odometer(board, args.index)
            elif args.command == "motor":
                cmd_motor(board, args)
            elif args.command == "direction":
                cmd_direction(board, args)
            elif args.command == "drive":
                cmd_drive(board, args)
            elif args.command == "stop":
                cmd_stop(board)
            elif args.command == "cr":
                cmd_cr(board, args)
            elif args.command == "info":
                cmd_info(board)
    except MCXBoardError as exc:
        print(f"Erreur de communication I2C : {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
