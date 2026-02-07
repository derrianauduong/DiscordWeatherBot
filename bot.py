import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import pytz
from datetime import datetime
from event_logic import get_weather_recommendations, get_todays_events, get_going_out_events
from weather import get_weather, format_weather
from google_auth import get_calendar_service
import os

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True  # Required so your bot can read messages

bot = commands.Bot(command_prefix="!", intents=intents)

service = get_calendar_service()

last_run_date = None

@tasks.loop(minutes=1)
async def daily_check():
    global last_run_date
    tz = pytz.timezone("Australia/Sydney")
    now = datetime.now(tz)

    # 1. Check time and date
    if now.hour == 7 and last_run_date != now.date():
        print(f"Check triggered at {now}")
        
        events = get_going_out_events(service)
        
        if not events:
            # OPTIONAL: Don't set last_run_date here if you want it to 
            # keep checking every minute until an event is found 
            # (though usually, if it's empty at 7am, it stays empty).
            print("No events found. Skipping today.")
            last_run_date = now.date() 
            return

        # 2. Get Channel (Use fetch to be safe)
        channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        user_id = os.getenv("DISCORD_USER_ID")

        recs = get_weather_recommendations(events)
        
        # 3. Build Message
        message = f"Hey <@{user_id}>! 📅 **Today's Going-Out Summary:**\n\n"
        for r in recs:
            # ... your loop logic ...
            # Accessing the new min/max:
            w = r["weather"]
            message += f"🌡️ Range: {w['temp_min']}°C - {w['temp_max']}°C\n"
        
        await channel.send(message)
        last_run_date = now.date() # Only set this after success
        print("Daily summary successfully sent.")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

    if not daily_check.is_running():
        daily_check.start()

@bot.command()
async def ping(ctx):
    channel = bot.get_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
    user_id = int(os.getenv("DISCORD_USER_ID"))
    await channel.send(f"<@{user_id}>")

@bot.command()
async def weather(ctx):
    lat = -33.8688
    lon = 151.2093
    now = datetime.now(pytz.timezone("Australia/Sydney"))

    w = get_weather(lat, lon, now)
    if not w:
        await ctx.send("No weather data available.")
        return

    await ctx.send(format_weather(w))

@bot.tree.command(name="events", description="Show today's calendar events")
async def events(interaction: discord.Interaction):
    await interaction.response.defer()

    events = get_todays_events(service)

    if not events:
        await interaction.followup.send("No events scheduled for today.")
        return

    message = "**Today's Events:**\n"
    for event in events:
        start_str = event["start"].get("dateTime")

        if start_str:
            dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            sydney = pytz.timezone("Australia/Sydney")
            local_dt = dt.astimezone(sydney)

            # Choose your preferred format:
            time_24h = local_dt.strftime("%H:%M")
            time_ampm = local_dt.strftime("%I:%M %p")

            message += f"- **{event['summary']}** at `{time_24h}` **({time_ampm})**\n"
        else:
            message += f"- **{event['summary']}** (All day)\n"

    await interaction.followup.send(message)

@bot.tree.command(name="goingout", description="Show today's going-out events")
async def going_out(interaction: discord.Interaction):
    await interaction.response.defer()

    events = get_going_out_events(service)

    if not events:
        await interaction.followup.send("No going-out events today.")
        return

    message = "**Today's Going-Out Events:**\n"
    for event in events:
        start_str = event["start"].get("dateTime")

        if start_str:
            dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            sydney = pytz.timezone("Australia/Sydney")
            local_dt = dt.astimezone(sydney)

            # Choose your preferred format:
            time_24h = local_dt.strftime("%H:%M")
            time_ampm = local_dt.strftime("%I:%M %p")

            message += f"- **{event['summary']}** at `{time_24h}` **({time_ampm})**\n"
        else:
            message += f"- **{event['summary']}** (All day)\n"


    await interaction.followup.send(message)

bot.run(os.getenv("DISCORD_TOKEN"))



