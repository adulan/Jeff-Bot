"""
MIT License

Copyright (c) 2018-2019 Evan Liapakis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from discord.ext import commands
from setup import init_files
import discord
import random
import ext

init_files()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

client = commands.Bot('j.', intents=intents)

tok = open('token')
token = tok.read().strip()
tok.close()


@client.event
async def on_ready():
    print("Bot online.")
    print("Username: {}".format(client.user.name))
    print("ID: {}".format(client.user.id))
    if ext.is_vote_time():
        await client.change_presence(activity=discord.Game(name="{} tribal council".format(ext.get_tribal())))
    else:
        await client.change_presence(activity=discord.Game(name="j.help"))


@client.command(pass_context=True)
async def add(ctx, *args):
    """Adds a player, idol, or strike to the database"""
    if not ext.host(ctx):
        # Checks to see if user running the command is a host
        await ctx.send("You are not a host.")
        return 1

    if len(args) != 2:
        # Check for valid amount of arguments
        if len(args) == 3:
            cmd, user_id, name = args
        else:
            await ctx.send("Please enter a valid amount of arguments.")
            return 1
    else:
        cmd, player = args
        if not ext.exists("players.csv", player):
            await ctx.send("Player does not exist.")
            return 1

    if cmd == "player":
        if ext.exists("players.csv", user_id):
            # Check if player already exists
            await ctx.send('Player already exists.')
        elif user_id not in [mem.name for mem in ctx.guild.members]:
            # Check for player in server
            await ctx.send("There is no {} in the server.".format(user_id))
            await ctx.send(ctx.guild.members)
        else:
            # Write to players.csv with the player data
            player = ctx.message.author.name
            ext.Player(player).write(name, 'no')
            # Change nickname and role
            user = ext.get_player_object(ctx, user_id)
            role = ext.get_role_object(ctx, "Castaway")
            await ctx.send("Added user *{}* as *{}*".format(user_id, name))

            try:
                await client.change_nickname(user, name)
            except discord.errors.Forbidden:
                await ctx.send("Unable to change nickname. Please manually change {}'s nickname to {}.".format(user_id, name))
            except AttributeError:
                await ctx.send("Unable to change nickname. Please manually change {}'s nickname to {}.".format(user_id, name))

            try:
                await client.add_roles(user, role)
            except discord.errors.Forbidden:
                await ctx.send("Unable to add role *Castaway*. Please manually add role to player {}.".format(user_id))
            except AttributeError:
                await ctx.send("Unable to add role *Castaway*. Please manually add role to player {}.".format(user_id))
    elif cmd == "idol":
        if ext.exists("idols.csv", player):
            # Check if player already has an idol
            # TODO: Allow players to have as many idols as they have found
            await ctx.send("Player already has an idol.")
        else:
            # Add idol
            ext.write("idols.csv", [player, "no"])
            await ctx.send("Added idol.")
    elif cmd == "strike":
        player = ext.Player(ext.get("players.csv", 1, player))
        if player.strikes == 2:
            await ctx.send("{} has 3 strikes and is eliminated".format(player.nick))
            if len(ext.get_players()) <= 10:
                role = "Juror"
            else:
                role = "Spectator"
            ext.remove_player(client, ctx, player.nick, role)
        else:
            player.write(strike=True)
            if player.strikes > 1:
                await ctx.send("{} now has {} strikes.".format(player.nick, player.strikes))
            else:
                await ctx.send("{} now has {} strike.".format(player.nick, player.strikes))
            nick = player.nick
            channel = ext.get_channel(ctx, "{}-confessional".format(nick.lower()))
            await client.edit_channel(channel, topic="Strikes: {}".format(player.strikes))
    else:
        await ctx.send("Invalid command. Commands are `player`, `idol`, and `strike`.")


@client.command(pass_context=True)
async def remove(ctx, *args):
    """Removes a player or idol from the database"""
    if not ext.host(ctx):
        await ctx.send("You are not a host.")
        return 1

    if len(args) != 2:
        await ctx.send("Please enter a valid amount of arguments.")
        return 1

    cmd, player = args

    if not ext.exists("players.csv", player):
        await ctx.send("Player does not exist.")
        return 1

    if cmd == "player":
        # Remove the player
        await ext.remove_player(client, ctx, player, "Spectator")
        await ctx.send("Removed {} from player list.".format(player))
    elif cmd == "idol":
        if ext.exists("idols.csv", player):
            ext.write("idols.csv", [player], True)
            await ctx.send("Removed idol.")
        else:
            await ctx.send("Player does not have an idol.")
    else:
        await ctx.send("Please enter a valid argument.")


@client.command(pass_context=True)
async def show(ctx, *args):
    """Lists either the players in the player list, the players who have
    voted, or the players who haven't voted"""

    if not ext.host(ctx):
        await ctx.send("You are not a host.")
        return 1

    if len(args) < 1:
        await ctx.send("Please enter an argument.")
        return 1

    if args[0] == "players":
        # Store player ids and then print data
        players = ext.get_players()
        data = ''
        # Store all data in one string
        # makes it quicker to print in Discord
        for item in players:
            data += "{}: {}, {} tribe".format(discord.utils.get(ctx.message.server.members, id=item.user_id), item.nick, item.tribe)
            if players[-1] != item:
                data += '\n'
        await ctx.send(data)
    elif args[0] == "voted":
        # Get players who have voted
        players = ext.get_players()
        voted = [player.nick for player in players if ext.voted(player.user_id)]
        if not voted:
            await ctx.send("Nobody has voted.")
        elif len(players) == len(voted):
            await ctx.send("Everybody has voted.")
        else:
            data = ''
            for player in voted:
                data += player
                if voted[-1] != player:
                    data += '\n'
            await ctx.send(data)
    elif args[0] == "not_voted":
        # Get players who haven't voted
        players = ext.get_players()
        not_voted = [player.nick for player in players if player.tribe == ext.get_tribal() and player.vote == "nobody"]
        if not not_voted:
            await ctx.send("Everybody has voted.")
        # Check to see if nobody has voted
        # HACK: this only works because any new data written is added
        # to the bottom
        # However, it changes O(n) to O(1)
        elif players[-1].vote != "nobody":
            await ctx.send("Nobody has voted.")
        else:
            data = ''
            for player in not_voted:
                data += player
                if not_voted[-1] != player:
                    data += '\n'
            await ctx.send(data)
    elif args[0] == "tribe":
        # Show the players in a tribe
        if len(args) < 2:  # Check for a second argument
            await ctx.send("Please enter a tribe.")
        elif not ext.exists("tribes.csv", args[1]):
            await ctx.send("Tribe {} does not exist.".format(args[1]))
        else:
            data = ''
            players = ext.get_players()
            for player in players:
                # Add nickname to data if player is in the tribe
                if player.tribe == args[1]:
                    data += player.nick
                    if players[-1] != player:
                        # Add a new line char if not last player in list
                        data += '\n'
            await ctx.send(data)
    elif args[0] == "votes":
        # Get each player's vote
        players = ext.get_players()
        if ext.is_vote_time():
            # Check to see if anyone has voted
            # HACK: this only works because any new data written is added
            # to the bottom
            # However, it changes O(n) to O(1)
            if players[-1].vote != "nobody":
                data = ""
                for player in players:
                    if player.tribe == ext.get_tribal():
                        if player.vote == "nobody":
                            data += "{} hasn't voted yet.".format(player.nick)
                        else:
                            data += "{} is voting {}.".format(player.nick, player.vote)
                        if player != players[-1]:
                            data += '\n'
                await ctx.send(data)
            else:
                await ctx.send("Nobody has voted.")
        else:
            await ctx.send("Players cannot vote.")
    elif args[0] == "idols":
        # Get all players with idols
        idols = ext.get("idols.csv", 1)
        if idols:
            data = ""
            for player in idols:
                using = ext.get("idols.csv", 2, player)
                if using == "yes":
                    data += "{}: using".format(player)
                else:
                    data += "{}: not using".format(player)
                if player != idols[-1]:
                    data += '\n'
            await ctx.send(data)
        else:
            await ctx.send("Nobody has an idol.")
    elif args[0] == "strikes":
        players = ext.get_players()
        data = ""
        for player in players:
            if player.strikes != 1:
                data += "{} has {} strikes.".format(player.nick, player.strikes)
            else:
                data += "{} has 1 strike.".format(player.nick)
            if player != players[-1]:
                data += "\n"
        await ctx.send(data)


@client.command(pass_context=True)
async def vote_time(ctx, tribe=''):
    """Manually toggle if players can vote or not"""

    if not ext.host(ctx):
        await ctx.send("You are not a host.")
        return 1

    if not tribe and not ext.is_vote_time():
        await ctx.send("Specify a tribe to allow players to vote.")
    elif not ext.is_vote_time() and ext.exists("tribes.csv", tribe):
        # Toggle vote time and set tribal to tribe
        await client.change_presence(game=discord.Game(name="{} tribal council".format(tribe)))
        ext.toggle()
        ext.set_tribal(tribe)
        await ctx.send("Players can now vote.")
    elif not ext.is_vote_time() and not ext.exists("tribes.csv", tribe):
        await ctx.send("Tribe {} does not exist.".format(tribe))
    else:
        await client.change_presence(game=discord.Game(name="j.help"))
        ext.toggle()
        ext.set_tribal('none')
        await ctx.send("Players can now no longer vote.")


@client.command(pass_context=True)
async def read_votes(ctx):
    """Manually read the votes"""

    if not ext.host(ctx):
        await ctx.send("You are not a host.")
        return 1

    # Toggle vote time
    ext.toggle()

    # Store votes in a list
    votes = []
    players = ext.get_players()
    for player in players:
        if ext.voted(player.user_id):
            votes.append(player.vote)
        elif player.tribe == ext.get_tribal():
            votes.append(player.nick)
        # Set vote to nobody
        player.write()

    # Get the order to read the votes and who is out
    final, out = ext.sort_votes(votes)
    idols = ext.get_idols()

    # Read out idols
    if idols:
        msg = ""
        for player in idols:
            if player == idols[0]:
                msg += "A reminder that {}".format(player)
            elif player == idols[-1]:
                msg += " and {}".format(player)
            else:
                msg += ", {}".format(player)
        if len(idols) > 1:
            msg += " are using idols."
        else:
            msg += " is using an idol."
        await ctx.send(msg)

    # Read the votes
    count = 1
    for vote in final:
        if count == 1:
            read = "1st vote: {}".format(vote)
        elif count == 2:
            read = "2nd vote: {}".format(vote)
        elif count == 3:
            read = "3rd vote: {}".format(vote)
        else:
            read = "{}th vote: {}".format(count, vote)
        if vote in idols:
            read += ", does not count"
        if count == len(final) and out is not None:
            read = "{} person voted out of Survivor: {}".format(ext.get_placing(), vote)
        count += 1
        await ctx.send(read)

    # Remove any idols being used
    for player in ext.get("idols.csv", 1):
        if ext.get("idols.csv", 2, player) == "yes":
            ext.write("idols.csv", [player], True)

    if out is None:
        # Print tie if more than two people with the highest count
        await ctx.send("We have a tie!")
    else:
        player = ext.Player(ext.get("players.csv", 1, out))
        obj = ext.get_player_object(ctx, player)
        await ctx.send("{}, the tribe has spoken.".format(obj.mention))
        jury = False
        with open("tribes.csv") as f:
            tribes = f.read().split("\n")
            if "," not in tribes:
                jury = True
        if jury:
            spec = "Juror"
        else:
            spec = "Spectator"

        nick = player.nick
        channel = ext.get_channel(ctx, "{}-confessional".format(nick.lower()))
        channel_name = "{}-{}".format(nick.lower(), ext.get_final_place())
        await client.edit_channel(channel, name="{}-{}".format(nick.lower(), ext.get_final_place()))

        # Remove the player
        await ext.remove_player(client, ctx, out, spec)

    # Reset tribal
    ext.set_tribal('none')
    await client.change_presence(game=discord.Game(name="j.help"))


@client.command(pass_context=True)
async def vote(ctx, player):
    """Vote for a player for Tribal Council (player's nickname)"""
    exists = ext.exists("players.csv", str(ctx.message.author.id))

    if not ext.is_vote_time():
        await ctx.send("You cannot vote at this time.")
        return 1

    if not exists:
        await ctx.send("You are not a player.")
        return 1

    user = ext.Player(str(ctx.message.author.id))
    tribe = ext.get_tribal()
    if "#" in player:
        await ctx.send("Please use a player's nickname, not their id.")
    elif tribe != user.tribe:
        await ctx.send("You are not in {} tribe.".format(tribe))
    elif tribe != ext.get("players.csv", 3, player):
        await ctx.send("{} is not in your tribe.".format(player))
    elif ext.voted(user.user_id):
        if ext.same(user.user_id, player):
            await ctx.send("Vote is already {}.".format(player))
        else:
            user.write(vote=player)
            await ctx.send("Vote changed to {}.".format(player))
    else:
        if ext.exists("players.csv", player):
            user.write(vote=player)
            await ctx.send("Voted for {}.".format(player))

            players = ext.get_players()
            voted = [player for player in players if ext.voted(player.user_id)]

            if len(players) == len(voted):
                await client.send_message(ext.get_channel(ctx, "host-channel"), content="{} Everyone has voted.".format(ext.get_role_object(ctx, "Host").mention))
        else:
            await ctx.send("That is not a player you can vote for.")


@client.command(pass_context=True)
async def sort_tribes(ctx, tribe1, tribe2, swap=''):
    """Sorts players into tribes. (tribe1, tribe2)"""

    if not ext.host(ctx):
        await ctx.send("You are not a host.")
        return 1

    players = ext.get_players()
    tribes = [tribe1, tribe2]
    counter = {tribe1: 0, tribe2: 0}
    for player in players:
        # Choose a random tribe
        while True:
            choice = random.choice(tribes)
            if counter[choice] < len(players) / 2:
                counter[choice] += 1
                break
        # Assign tribe to player
        player.write(tribe=choice)
        # Change roles
        role = ext.get_role_object(ctx, player.tribe)
        user = ext.get_player_object(ctx, player)
        try:
            await client.add_roles(user, role)
        except discord.errors.Forbidden:
            await ctx.send(("Unable to add {} role to {}. Forbidden."
                              "").format(player.tribe, player.nick))
        except AttributeError:
            await ctx.send(("Unable to add {} role to {}. Role does not "
                              "exist.").format(player.tribe, player.nick))

    # Write tribes to tribes.csv
    ext.write("tribes.csv", [tribe1, tribe2])

    if not swap:
        player_count = len(ext.get("players.csv", 1))
        with open("playernum", 'w') as f:
            f.write(str(player_count))


@client.command(pass_context=True)
async def merge_tribes(ctx, tribe):
    """Merges players into a single tribe. (tribe)"""

    if not ext.host(ctx):
        await ctx.send("You are not a host.")
        return 1

    players = ext.get_players()
    for player in players:
        # Change tribe to new merge tribe
        player.write(tribe=tribe)
        # Change roles
        role = ext.get_role_object(ctx, tribe)
        castaway = ext.get_role_object(ctx, "Castaway")
        user = ext.get_player_object(ctx, player)
        try:
            await client.replace_roles(user, role, castaway)
        except discord.errors.Forbidden:
            await ctx.send("Forbidden to add role.")
        except AttributeError:
            await ctx.send("Role {} does not exist.".format(tribe))

    # Delete old tribes from tribes.csv
    ext.write("tribes.csv", ext.get("tribes.csv", 1)[1], True)
    # Write new tribe to tribes.csv
    ext.write("tribes.csv", [tribe])


@client.command(pass_context=True)
async def rocks(ctx, *players):
    """Do rocks. (players who the vote was between)"""

    if not ext.host(ctx):
        await ctx.send("You are not a host.")
        return 1

    if not players:
        await ctx.send("Please specify players who are safe.")
        return 1

        await ctx.send("All players will draw a rock.")
        await ctx.send(("The player who draws the black rock "
                          "will be eliminated."))
        # Get all players who will draw
        player_list = ext.get_players()
        tribe = ext.get("players.csv", 3, players[0])
        choices = []
        for player in player_list:
            if player.nick not in players and player.tribe == tribe:
                choices.append(player)
        # Choose a random player
        out = random.choice(choices)
        obj = ext.get_player_object(ctx, out)
        await ctx.send("{} has the black rock.".format(out.nick))
        await ctx.send("{}, the tribe has spoken.".format(obj.mention))
        role = "Spectator"
        if len(players_list) <= 10:
            role = "Juror"
        else:
            role = "Spectator"
        # Eliminate
        await ext.remove_player(client, ctx, out.nick, role)


@client.command(pass_context=True)
async def use_idol(ctx):
    """Allow a player to use their idol"""
    player = ext.get("players.csv", 2, str(ctx.message.author.id))
    if ext.exists("players.csv", player):
        if ext.exists("idols.csv", player):
            if ext.get("idols.csv", 2, player) == "yes":
                await ctx.send("You are already using your idol.")
            else:
                ext.write("idols.csv", [player, "yes"])
                await ctx.send("I can confirm this is a hidden immunity idol.")
        else:
            await ctx.send("You do not have an idol.")
    else:
        await ctx.send("You are not a player.")

client.run(token)
