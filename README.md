# netatmo-trmnl

A command-line tool for interacting with Netatmo smart home devices.

## Features

- Authenticate with your Netatmo account
- Retrieve and display device data (thermostats, weather stations, etc.)
- Control compatible Netatmo devices from the terminal
- Scriptable for automation and integration

## Installation

```bash
git clone https://github.com/yourusername/netatmo-trmnl.git
cd netatmo-trmnl
pip install -r requirements.txt
```

## Usage

```bash
python netatmo-trmnl.py --help
```

Example: List all devices

```bash
python netatmo-trmnl.py devices list
```

## Configuration

1. Obtain your Netatmo API credentials from the [Netatmo Developer Portal](https://dev.netatmo.com/).
2. Set your credentials as environment variables or in a `.env` file:

```
NETATMO_CLIENT_ID=your_client_id
NETATMO_CLIENT_SECRET=your_client_secret
NETATMO_USERNAME=your_email
NETATMO_PASSWORD=your_password
```

## Contributing

Contributions are welcome! Please open issues or submit pull requests.

## License

MIT License