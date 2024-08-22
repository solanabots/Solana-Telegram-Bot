import json
import curses
import argparse
from setuptools import setup, find_packages

CONFIG_FILE = 'config.json'

def read_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        return {}

def write_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def display_menu(stdscr, current_config):
    curses.curs_set(0)  # Hide cursor
    stdscr.clear()
    stdscr.refresh()

    k = 0
    cursor_y = 0

    while k != ord('q'):
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        title = "Config Manager - Press 'q' to exit"
        subtitle = "Use arrow keys to navigate, Enter to edit"
        statusbarstr = "Press 'q' to exit | STATUS BAR"

        if k == curses.KEY_DOWN:
            cursor_y = (cursor_y + 1) % len(current_config)
        elif k == curses.KEY_UP:
            cursor_y = (cursor_y - 1) % len(current_config)
        elif k == curses.KEY_ENTER or k in [10, 13]:
            edit_value(stdscr, cursor_y, current_config)

        stdscr.addstr(0, 0, title, curses.A_BOLD)
        stdscr.addstr(1, 0, subtitle)

        for idx, (key, value) in enumerate(current_config.items()):
            x = 2
            y = 3 + idx
            if idx == cursor_y:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(y, x, f"{key}: {value}")
                stdscr.attroff(curses.color_pair(1))
            else:
                stdscr.addstr(y, x, f"{key}: {value}")

        stdscr.addstr(height-1, 0, statusbarstr)
        stdscr.refresh()
        k = stdscr.getch()

def edit_value(stdscr, index, current_config):
    curses.echo()
    keys = list(current_config.keys())
    key = keys[index]
    value = current_config[key]

    stdscr.clear()
    stdscr.addstr(0, 0, f"Editing '{key}' (current value: {value})")
    stdscr.addstr(1, 0, "Enter new value: ")
    stdscr.refresh()

    new_value = stdscr.getstr(1, 16, 20).decode('utf-8')
    current_config[key] = type(value)(new_value)
    write_config(current_config)
    curses.noecho()

def main():
    parser = argparse.ArgumentParser(description="Manage config.json")
    parser.add_argument('--view', action='store_true', help='View the current configuration')
    parser.add_argument('--edit', action='store_true', help='Edit the current configuration')

    args = parser.parse_args()

    current_config = read_config()

    if args.view:
        for key, value in current_config.items():
            print(f"{key}: {value}")
    elif args.edit:
        curses.wrapper(display_menu, current_config)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

setup(
    name="config_manager",
    version="0.1",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'config_manager = __main__:main',
        ],
    },
)
