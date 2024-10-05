# Telegram bot that opens X links fully to the chat
Name on telegram: @yapOpenerBot

## For getting the bot running locally
### install
```
python3 -m venv venv

pip install -r requirements.txt

playwright install
```

### run in dev
```
python3 bot.py
```

### to run in background
```
nohup ./venv/bin/python3 bot.py &
```

### to see background process output
```
tail -f nohup.out 
```
### to kill the bg process
```
ps aux | grep python

kill <id>
```
