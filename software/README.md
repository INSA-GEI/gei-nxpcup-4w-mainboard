# mcx_i2c — Communication I2C avec le microcontrôleur MCXA153

Bibliothèque Python + CLI d'exemple pour dialoguer, depuis Linux (FRDM-IMX8MPLUS),
avec le microcontrôleur MCXA153 connecté sur I2C2 et simulant un capteur/actionneur
robotique (moteurs, servo de direction, odomètres, tension batterie, registre de
contrôle).

## Installation

```bash
pip install -r requirements.txt
# ou directement :
pip install smbus2
```

L'utilisateur doit avoir accès au périphérique `/dev/i2c-N` correspondant à I2C2
(généralement membre du groupe `i2c`, ou exécution via `sudo`).

Pour identifier le numéro de bus correspondant à I2C2 sur la carte :

```bash
i2cdetect -l
i2cdetect -y <N>      # doit faire apparaître le périphérique à l'adresse 0x42
```

## Carte des registres (rappel)

| Registre | Index | Accès | Contenu |
|---|---|---|---|
| `ID`      | 0x00 | RO | Identifiant carte (toujours `0x10`) |
| `VER`     | 0x01 | RO | Version firmware |
| `VBAT_1R`/`VBAT_2R` | 0x02-0x03 | RO | Tension batterie (mV, uint16 LE) |
| `ODO1_1R`..`ODO1_4R` | 0x04-0x07 | RO | Odomètre 1 (uint32 LE) |
| `ODO2_1R`..`ODO2_4R` | 0x08-0x0B | RO | Odomètre 2 (uint32 LE) |
| `MOT1`    | 0x0C | RW | Moteur gauche, duty cycle 0-100 % |
| `MOT2`    | 0x0D | RW | Moteur droit, duty cycle 0-100 % |
| `DIR`     | 0x0E | RW | Direction servo, int8 signé -100..100 |
| `CR`      | 0x0F | RW | Registre de contrôle / status système |

> **Registre `CR` (arrêt système)** : le firmware fourni expose ce registre comme
> un registre de contrôle RW générique, sans documenter précisément l'usage de
> chaque bit dans le code source transmis. La bibliothèque propose une convention
> par défaut (`ControlBit.SHUTDOWN_REQUEST` = bit 0, `ControlBit.SHUTDOWN_ACK` =
> bit 1) à ajuster si votre implémentation MCU utilise une autre convention —
> vous pouvez aussi utiliser directement `get_control_register()` /
> `set_control_register()` pour un accès à la valeur brute.

## Utilisation de la bibliothèque

```python
from mcx_i2c import MCXBoard

with MCXBoard(bus=2) as board:          # /dev/i2c-2
    print(board.get_status())            # instantané complet (1 seule transaction I2C)

    print(board.get_vbat_mv(), "mV")
    print(board.get_odometers())         # (odo1, odo2)

    board.set_motors(30, 30)             # moteurs gauche/droit à 30 %
    board.set_direction(0)               # direction neutre

    # ou en une seule transaction :
    board.set_motors_and_direction(30, 30, 0)

    if board.is_shutdown_requested():
        board.acknowledge_shutdown()
```

Toutes les erreurs de communication (bus absent, NACK, etc.) lèvent une
`MCXBoardError`. Les valeurs hors plage (duty cycle, direction, registre) lèvent
une `ValueError` avant tout accès matériel.

## Utilisation de la CLI (`mcx_cli.py`)

```bash
# Instantané complet
./mcx_cli.py --bus 2 status

# Supervision en continu (Ctrl+C pour arrêter)
./mcx_cli.py --bus 2 status --watch --interval 0.5

# Tension batterie
./mcx_cli.py --bus 2 vbat

# Odomètres
./mcx_cli.py --bus 2 odometer
./mcx_cli.py --bus 2 odometer 1

# Moteurs
./mcx_cli.py --bus 2 motor get 1
./mcx_cli.py --bus 2 motor set 1 25

# Direction
./mcx_cli.py --bus 2 direction get
./mcx_cli.py --bus 2 direction set -30

# Moteurs + direction en une seule transaction I2C
./mcx_cli.py --bus 2 drive 40 40 0

# Arrêt d'urgence (moteurs à 0, direction neutre)
./mcx_cli.py --bus 2 stop

# Registre de contrôle
./mcx_cli.py --bus 2 cr get
./mcx_cli.py --bus 2 cr set 0x00
./mcx_cli.py --bus 2 cr shutdown-requested
./mcx_cli.py --bus 2 cr ack-shutdown

# Identification
./mcx_cli.py --bus 2 info
```

## Détails du protocole bas niveau

- **Lecture** : la bibliothèque envoie l'index du registre de départ (sans
  STOP), puis lit N octets consécutifs — le MCU incrémente son pointeur
  interne à chaque octet transmis, avec retour à 0 après `CR` (0x0F).
- **Écriture** : la bibliothèque envoie `[index_registre, data0, data1, ...]`
  en une seule transaction — seuls les registres RW (`MOT1` à `CR`) sont
  réellement modifiés par le MCU ; une écriture sur un registre RO est
  silencieusement ignorée côté firmware (mais refusée en amont par la
  bibliothèque via `MCXBoardError`).

Ce protocole correspond exactement à une transaction "I2C block" (et non au
protocole SMBus block standard, qui inclut un octet de taille), ce qui est
directement pris en charge par `smbus2.read_i2c_block_data` /
`write_i2c_block_data`.
