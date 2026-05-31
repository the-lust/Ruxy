import discord
import requests
from discord import app_commands

# if the value starts with "$", then the following should be interpreted as a key for this
# if a key does not exist, https://github.com/rux-lang/<key> gets checked.
# aliases & links in this directory are assumed to be correct and won't be checked.
# value must end with "/{owner}/repo" if it's not an alias -> no branches
REPOS = {
    "rux": "https://github.com/rux-lang/Rux",
    "std": "https://github.com/rux-lamg/Std",
    "windows": "https://github.com/rux-lang/Windows",
    "linux": "https://github.com/rux-lang/Linux",
    "bsd": "https://github.com/rux-lang/BSD",
    "macos": "https://github.com/rux-lang/MacOS",
    "bot": "https://github.com/rux-lang/Ruxy",
    "website": "https://github.com/rux-lang/Web",
    "illumos": "https://github.com/rux-lang/Illumos",
    "tests": "https://github.com/rux-lang/Tests",
    "tutorials": "https://github.com/rux-lang/Tutorials",
    "zed": "https://github.com/rux-lang/Zed",
    "vscode": "https://github.com/rux-lang/VSCode",
    "sublime": "https://github.com/rux-lang/SublimeText",

    # alias
    "vsc": "$vscode",
    "sublimetext": "$sublime",
}

async def repo_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name="Rux (Compiler)", value="rux"),
        app_commands.Choice(name="Standard Library", value="std"),
        app_commands.Choice(name="Windows Library", value="windows"),
        app_commands.Choice(name="Linux Library", value="linux"),
        app_commands.Choice(name="BSD Library", value="bsd"),
        app_commands.Choice(name="MacOS Library", value="macos"),
        app_commands.Choice(name="Illumos Library", value="illumos"),
        app_commands.Choice(name="Ruxy Bot", value="bot"),
        app_commands.Choice(name="Rux Website", value="website"),
        app_commands.Choice(name="Rux (Tests)", value="tests"),
        app_commands.Choice(name="Tutorials", value="tutorials"),
        app_commands.Choice(name="Zed (Extension)", value="zed"),
        app_commands.Choice(name="VS Code (Extension)", value="vscode"),
        app_commands.Choice(name="Sublime Text (Extension)", value="sublime")
    ]



def setup(tree, client):
    @tree.command(
        name="repo",
        description="Get a link to a Rux repository"
    )
    @app_commands.autocomplete(repository=repo_autocomplete)
    async def repo(
        interaction: discord.Interaction,
        repository: str,
        branch: str = "main"
    ):
        
        deferred: bool = False
        repo_name: str = repository
        branch_name: str = ""
        url: str = REPOS.get(repository, "")
        if url.startswith("$"): # alias
            repo_name = f"{url.removeprefix("$")} (alias `{repository}`)"
            url = REPOS.get(url.removeprefix("$"), "")
        elif url == "": # empty -> check url
            r_url = f"https://api.github.com/repos/rux-lang/{repository}"
            await interaction.response.defer()
            deferred = True

            # check if a repo exists
            r = requests.get(r_url, headers={"User-Agent": "repo-check"})
            if r.status_code == 200:
                url = f"https://github.com/rux-lang/{repository}"
            else:
                await interaction.followup.send(
                    "This repository does not exist.",
                    ephemeral=True
                )
        
        if branch != "main":
            if not deferred:
                await interaction.response.defer()
                deferred = True

            repo_parts = url.split("/")
            # "{owner}/{repo}"
            repo_url = repo_parts[-2] + "/" + repo_parts[-1]
            
            r_url = f"https://api.github.com/repos/{repo_url}/branches/{branch}"
            r = requests.get(r_url, headers={"User-Agent": "repo-branch-checker"})
            if r.status_code == 200:
                url = f"https://github.com/{repo_url}/tree/{branch}"
                branch_name = branch
            else:
                await interaction.followup.send(
                    f"Repository `{repository}` has no branch `{branch}`",
                    ephemeral=True
                )

        view = discord.ui.View()

        view.add_item(
            discord.ui.Button(
                label=f"Open {repository}",
                url=url
            )
        )

        branch_string: str = f"\nBranch: **{branch_name}**" if branch_name != "" else ""

        embed = discord.Embed(
            title="Repository",
            description=f"Repository: **{repo_name}**{branch_string}",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="URL",
            value=url,
            inline=False
        )

        if deferred:
            await interaction.followup.send(
                embed=embed,
                view=view
            )
        else:
            await interaction.response.send_message(
                embed=embed,
                view=view
            )