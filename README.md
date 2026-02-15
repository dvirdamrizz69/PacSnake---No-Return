# PacSnake---No-Return

A grid-based arcade game built with Python and Arcade.
Inspired by Pac-Man — but with a deadly twist.

Every move leaves a fading trail behind you.
Cross your own path, and you lose a life.

Core Concept
------------
- Classic maze navigation
- Dynamic ghost AI with chase and scatter behavior
- Power pellets that trigger frightened mode
- Infinite wave progression with scaling difficulty
- Precision tile-based movement with buffered turns
- Tunnel wrapping and grid-aligned AI logic
- Neon-styled visuals and animated sprites

Gameplay Features
-----------------
- Trail System: Movement leaves temporary hazard tiles.
- Ghost Personalities:
  * Blinky (direct chase)
  * Pinky (predictive targeting)
  * Inky (vector-based targeting)
  * Clyde (distance-based behavior)
- Power Mode: Eat a power pellet to reverse the threat.
- Wave Scaling: Trail duration increases with each wave.
- Responsive Controls: Turn buffering and tile snapping.

Controls
--------
W  - Move Up
S  - Move Down
A  - Move Left
D  - Move Right
Enter - Start / Restart
ESC - Exit

Installation
------------
1. Install dependency:
   pip install arcade

2. Run the game:
   python main.py

Tech Stack
----------
- Python 3
- Arcade 3.x
- Grid-based collision system
- Manhattan-distance ghost AI
- Spatial hashing for performance

Project Focus
-------------
This project explores deterministic grid movement, classic arcade AI design, 
state-driven architecture, and risk-based gameplay mechanics.
