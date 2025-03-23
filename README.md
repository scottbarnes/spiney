# A bot based on [discord.py](https://discordpy.readthedocs.io/en/stable/)

Setup:
1. `git clone git@github.com:scottbarnes/spiney.git && cd spiney`
2. Edit `.env` and add `DISCORD_BOT_API_KEY`, `GOOGLE_MAPS_API_KEY`, and `OPENWEATHER_API_KEY` (API version 2.5).
3. `docker compose build`
4. Change or copy out the `adminer` settings in `compose.yaml`. See https://www.adminer.org/en/password/ for using `login-password-less.php` to authenticate for SQLite with a single password.
5. `docker compose up`

## Database migration
This uses [SQLAlchemy 2.0.x](https://www.sqlalchemy.org/) and [Alembic](https://alembic.sqlalchemy.org/en/latest/).
After modify a database model, with the assumption you're working in a `venv`:
```bash
$ alembic revision --autogenerate -m "Change to some database model"
$ alembic upgrade head
$ git add <alembic/migration_file.txt>
$ git commit -m "Change to some database model"
$ git push origin HEAD   # When ready to finally push the changes.
```
To do this within the Docker containers (e.g. because the deployment is elsewhere in Docker), do the above and:
```bash
$ git pull origin main       # Get the new changes
$ cp data/bot.sqlite{,.bak}  # Back up the DB.
$ docker compose build
$ docker compose stop
$ docker compose run discordbot alembic upgrade head
```

Ideally the output will be something like:
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 9de4b56d1b4f, Initial migration
INFO  [alembic.runtime.migration] Running upgrade 9de4b56d1b4f -> 25c056e652aa, Add weather_location to users
```
If all goes well, run the bot once more.
```
$ docker compose up          # Or docker compose up -d
```
