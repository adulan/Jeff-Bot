import os

def init_files():
# Create all needed files
    with open("players.csv", 'w+'):
        pass

    with open("tribes.csv", 'w+') as f:
        f.write("voting,none\n")

    with open("vote_time", 'w+') as f:
        f.write('0')

    with open("idols.csv", 'w+') as f:
        pass

    with open("token", 'w+') as f:
        f.write(os.getenv("DISCORD_TOKEN"))

    with open("playernum", 'w+') as f:
        f.write("0")
