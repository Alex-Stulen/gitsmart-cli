import click

from gitsmart.commands.analyze import analyze
from gitsmart.commands.commit import commit
from gitsmart.commands.config import config_cmd
from gitsmart.commands.configure import configure
from gitsmart.commands.logout import logout
from gitsmart.commands.logs import logs
from gitsmart.commands.review import review
from gitsmart.commands.search import search
from gitsmart.commands.usage import usage
from gitsmart.commands.whoami import whoami


@click.group()
def main():
    """
    GitSmart — AI-powered Git workflow assistant.
    Make your life easier by working with git. And spare time to spend on something more valuable for you! :)
    """


main.add_command(configure)
main.add_command(config_cmd)
main.add_command(whoami)
main.add_command(usage)
main.add_command(logs)
main.add_command(commit)
main.add_command(review)
main.add_command(analyze)
main.add_command(search)
main.add_command(logout)
