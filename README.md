# CTF Dungeon

TODO: Readme and documentation

# Installation

## Download project from github

```
git clone https://github.com/smythtech/ctfdungeon
```

## Get uwsgi

This project has been tested with the version of uwsgi that can be aquired through pip

```
pip install uwsgi
```

At this stage try running uwsgi.

```
uwsgi

```

If you are unable to run uwsgi as a command you may have to locate the binary and create a symbolic link.

```
sudo find / -name uwsgi
```

When you locate the binmary you can create the symbolic link like so

```
sudo ln -s /path/to/uwsgi /usr/bin/uwsgi
```
 
You can now run uwsgi as a command.



# Running CTF Dungeon 

CTF Dungeon can be run using uwsgi. The following command will launch CTF Dungeon locally on port 8080.

```
uwsgi conf.ini 
```
