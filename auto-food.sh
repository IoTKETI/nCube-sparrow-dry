  
#!/usr/bin/sh

sudo chmod 777 /home/pi/nCube-sparrow-dry/
cd /home/pi/nCube-sparrow-dry
sudo chmod 777 *
python3 start.py
git stash
git pull
sleep 5
git stash pop
python3 exec.py &
sleep 2
pm2 start thyme.js
