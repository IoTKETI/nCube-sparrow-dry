  
#!/usr/bin/sh

cd /home/pi/nCube-sparrow-dry
python3 start.py
git stash
git pull
sleep 5
git stash pop
pm2 start thyme.js