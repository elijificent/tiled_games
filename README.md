# Tiled Games

(Currently) Tools for building map/tile based games,
will eventually hold the games themselves or be converted
to a library to be used elsewhere

## Quickstart
1. Create vitural environment
```bash
python -m venv .venv
```
2. Activate the environment 
```bash
source .venv/bin/activate
```
3. _[Optional]_ Upgrade pip 
```bash
python -m pip install --upgrade pip
```
4. Install requirements 

```bash
make install_requirements
```

## Useful commands
- `make html`: generate sphinx documentation
- `make format`: run black formatter to check for violations
- `make format_fix`: tun black formatter to correct violation
- `make test`: run formatter and tests
- `make test_light`: run only tests
- `make snapshots`: update test snapshots
