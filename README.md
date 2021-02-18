# Customizable-Temple-Terrain-Generator
![Alt text](/screenshot.png?raw=true)
## UI
* Seed: used for the randomization\
* Randomize: gain a random seed\
* Root Chance: the amount of root-blocks spawned\
* First Layer Amount: amount of blocks used on the first elevation layer\
* Second Layer Amount: amount of blocks used on the second elevation layer\
* Maximum Distance from Center: for the root-blocks\
## Customization
The dungeon_resources folder is generated automatically.
The folder is to be populated with the given resources.
Elements can be added using .obj and .json files possessing the same name.
## Adding Blocks
* size_x/y/z: designates a collision box of those particular size multiplied by 10
* the tags it contains designates the stage of generation at which the block may be used
  * base blocks are spawned first
  * infrastructure blocks second
  * stairs blocks thirdly
* freq: designates a weight at which this block is chosen over the others (arbitrarily defaulted to 1)
* connector_input/outputs: contain a list of coordinates which indicate the positions at which the block connects to another (positions relative to size_x,y,z 10 units)
* pillar key: optional; it is a list which contains points in which pillars will be spawned underneath the block (positions relative to object center)
* props key: optional; it is a list which contains a prop type, followed by its chance to be spawned, and a series of x, y, z coordinates (positions relative to object center)
