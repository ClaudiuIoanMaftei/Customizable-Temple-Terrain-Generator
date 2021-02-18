import maya.cmds as cmds
import os
import json
import random
import maya.mel as mel
import time
import math
from functools import partial


"""
dungeonBlocksData{}
    blocklist - list of block names
    propList - list of prop names
    <tag>List - list of blocks/props of that tag
    rooms + blockName - json data
    props + propName - json data
    <block> + input/output - list of its connectors for input/output
"""

#Constants / Variables
workspacePath=cmds.workspace(q=True, rd=True) + "dungeon_resources/"
seedString=None
seed=None
vertexPositions=None

#Utility Functions
def weightedChoice(choices,chances):
    max_chance=0
    item_chance=[] #contains the chance intervals
    for i in range(len(choices)):
        max_chance+=chances[i]
        item_chance.append(max_chance)
        
    choice=random.random() * max_chance #generate between 0 and 1 multiplied by max_chance (so 0 and max_chance)
    
    for i in range(len(choices)):
        if item_chance[i]>choice:
            return(choices[i])
            
    return choices[len(choices)-1]
    
def deleteAll():
    for element in cmds.ls():
        if "block" in element:
            if cmds.objExists(element):
                cmds.delete(element)
        elif "prop" in element:
            if cmds.objExists(element):
                cmds.delete(element)
        elif "collisionBox" in element:
            if cmds.objExists(element):
                cmds.delete(element)
    cmds.select(clear=True)

def detectCollision(obj1,obj2,*args):
    collided=None
    
    duplicateInputRoom=cmds.duplicate(obj1,n=obj1+'d', renameChildren=True)
    duplicateOutputRoom=cmds.duplicate(obj2,n=obj2+'d', renameChildren=True)
    
    cmds.scriptEditorInfo(historyFilename=workspacePath+"log.txt", writeHistory=True) #start noting the history
    cmds.polyCBoolOp(duplicateInputRoom[0],duplicateOutputRoom[0],op=3,n='auxIntersection') #try for warning
    cmds.scriptEditorInfo(writeHistory=False) #stop recording information
    with open(workspacePath+"log.txt",'r') as f:
        lines= f.readlines()
        collided = len(lines)==0 #if the file is empty of any error - then there is an intersection/collision
    os.remove(workspacePath+"log.txt") #remove it
    
    cmds.delete(duplicateInputRoom)
    cmds.delete(duplicateOutputRoom)
    cmds.delete('auxIntersection')
    
    return collided
   
def generateSeed(newSeed=None): #takes one input or None for randomization
    seedString=newSeed
    random.seed(seedString)
    seed=random.random()*1000
    cmds.setAttr("Noise.time",seed)
        

def getVertexList():
    global vertexPositions
    
    vertexPositions=[]
    amount=cmds.polyEvaluate("Terrain",vertex=True)
    for i in range(amount):
        values=cmds.xform("Terrain.vtx["+str(i)+"]",q=True,worldSpace=True,translation=True)
        vertexPositions.append(values)
        
#---------------------------------------------------------------------------------------
class DungeonGenerator():
    def __init__(self):
        if not os.path.exists(workspacePath):
            os.makedirs(workspacePath)
        self.resourcePath=workspacePath
        
        #Loading
        self.dungeonBlocksData={"blockList":[],
            "baseList":[],
            "infrastructureList":[],
            "bridgeList":[],
            "stairsList":[],
            
            "propList":[],
            "pillarList":[],
            "treeList":[],
            "grassList":[]
        }
        #Blocks
        for file in cmds.getFileList(folder=self.resourcePath+"rooms/", filespec='*.json'):
            blockName=file.replace('.json','')
            with open(self.resourcePath+"rooms/"+file, "r") as fileHandle:
                self.dungeonBlocksData["rooms"+blockName]=json.load(fileHandle)
                
            self.dungeonBlocksData["blockList"].append(blockName)
            for tag in self.dungeonBlocksData["rooms"+blockName]["tags"]:
                self.dungeonBlocksData[tag+"List"].append(blockName)
        #Props
        for file in cmds.getFileList(folder=self.resourcePath+"props/", filespec='*.json'):
            propName=file.replace('.json','')
            with open(self.resourcePath+"props/"+file, "r") as fileHandle:
                self.dungeonBlocksData["props"+propName]=json.load(fileHandle)
                
            self.dungeonBlocksData["propList"].append(propName)
            for tag in self.dungeonBlocksData["props"+propName]["tags"]:
                self.dungeonBlocksData[tag+"List"].append(propName)
                
        
        #Constants      
        self.blockList=[]
        self.blockIndex=-1
        self.blockConnectors={}
        self.blockPresets={}
        
        self.inputConnectorList=[]
        self.currentConnector=0
        self.outputConnectorList=[]
        self.currentPillar=0
        self.pillarList=[]
        
        self.collisionBoxes={}
        self.collisionUnions=[]
        self.triedConnections=[]
        
        self.propList=[]
        self.propIndex=-1
        self.propConnectors=[]
        self.propProperties={}
        self.currentPropConnector=0
        
        #Editable
        self.baseAmount=15
        self.structureAmount=15
        self.distanceAmount=200
        self.rootsAmount=1.0
       
        
        
    def importObj(self,target,name="myobj"):
        cmds.file(self.resourcePath + target, i=True, groupReference=True, groupName=name)
        
    def addToCollisionUnion(self,obj):
        unionAmounts=len(self.collisionUnions)
        if self.blockIndex>=15*unionAmounts: #amount of blocks in a single union
            cmds.rename(obj,"collisionUnion"+str(len(self.collisionUnions)))
            self.collisionUnions.append("collisionUnion"+str(len(self.collisionUnions)))
        else:
            self.collisionUnions[unionAmounts-1]=cmds.polyCBoolOp(self.collisionUnions[unionAmounts-1],obj, op=1,ch=False)[0]
        
    def spawnProp(self,tag=None):
        self.propIndex+=1
        
        #Spawn prop
        localPresetList=[]
        if tag==None:
            localPresetList=self.dungeonBlocksData["propList"]
        else:
            localPresetList=self.dungeonBlocksData[tag+"List"]
        weights=[]
        for prop in localPresetList:
            weights.append(self.dungeonBlocksData["props"+prop]["freq"])
            
        propPreset=weightedChoice(localPresetList,weights)
            
        propName="prop"+str(self.propIndex)
        self.importObj("props/"+propPreset+".obj",propName)
        
        
    def spawnBlock(self,tag=None):
        self.blockIndex+=1
        
        #Spawn block
        localPresetList=[]
        if tag==None:
            localPresetList=self.dungeonBlocksData["blockList"]
        else:
            localPresetList=self.dungeonBlocksData[tag+"List"]
        weights=[]
        for block in localPresetList:
            weights.append(self.dungeonBlocksData["rooms"+block]["freq"])
            
        blockPreset=weightedChoice(localPresetList,weights)
            
        blockName="block"+str(self.blockIndex)
        self.importObj("rooms/"+blockPreset+".obj",blockName)
        self.blockPresets[blockName]=blockPreset
        
        #Spawn collision
        collisionName="collisionBox"+str(self.blockIndex)
        self.collisionBoxes[blockName]=collisionName
        size_x=self.dungeonBlocksData["rooms"+blockPreset]["size_x"] * 10
        size_y=self.dungeonBlocksData["rooms"+blockPreset]["size_y"] * 10
        size_z=self.dungeonBlocksData["rooms"+blockPreset]["size_z"] * 10
        cmds.polyCube(name=collisionName,width=size_x,height=size_y,depth=size_z)
        cmds.move(size_x/2,size_y/2,size_z/2,collisionName)
        
        #Spawn connectors
        localInputConnectors=[]
        for input in self.dungeonBlocksData["rooms" + blockPreset]["connector_input"]:
            connectorName='connector'+str(self.currentConnector)
            cmds.sphere(name=connectorName)
            self.inputConnectorList.append(connectorName)
            localInputConnectors.append(connectorName)
            self.currentConnector+=1
            
            cmds.move(input[0],input[1],input[2],connectorName)
            cmds.parent(connectorName,blockName,relative=True)
        localOutputConnectors=[]
        for output in self.dungeonBlocksData["rooms" + blockPreset]["connector_output"]:
            connectorName='connector'+str(self.currentConnector)
            cmds.sphere(name=connectorName)
            self.outputConnectorList.append(connectorName)
            localOutputConnectors.append(connectorName)
            self.currentConnector+=1
            
            cmds.move(output[0],output[1],output[2],connectorName)
            cmds.parent(connectorName,blockName,relative=True)
            
        self.blockConnectors[blockName+"input"]=localInputConnectors
        self.blockConnectors[blockName+"output"]=localOutputConnectors
        
        #Spawn pillars
        if "pillars" in self.dungeonBlocksData["rooms" + blockPreset].keys():
            for pillar in self.dungeonBlocksData["rooms" + blockPreset]["pillars"]:
                pillarName='pillar'+str(self.currentPillar)
                cmds.sphere(name=pillarName)
                self.pillarList.append(pillarName)
                self.currentPillar+=1
                
                cmds.move(pillar[0]+5,pillar[1],pillar[2]+5,pillarName)
                cmds.parent(pillarName,blockName,relative=True)
                
        #Spawn props
        if "props" in self.dungeonBlocksData["rooms" + blockPreset].keys():
            for prop in self.dungeonBlocksData["rooms" + blockPreset]["props"]:
                propName='propSpawn'+str(self.currentPropConnector)
                cmds.sphere(name=propName)
                self.propConnectors.append(propName)
                self.currentPropConnector+=1
                
                self.propProperties[propName]=[prop[0],prop[1]]
                cmds.move(prop[2]+5,prop[3],prop[4]+5,propName)
                cmds.parent(propName,blockName,relative=True)
        
    def generateRoots(self):
        #Generate Bedrock Layer - to prevent underground structures
        cmds.duplicate("Terrain",name="bedrock")
        cmds.move(0,-10,0,"bedrock", r=True)
       
            
        for place in vertexPositions:
            #Generate Roots
            chance= place[1]/100.0 *0.05 #encourage higher places
            distance=math.sqrt(place[0]**2 + place[2]**2)
            chance*= 1 - distance / 500 #encourage closer to center
            chance*=self.rootsAmount
            if chance > random.random() and distance<=self.distanceAmount:
                self.spawnBlock("base")
                place[0]=10 * math.floor(place[0]/10)
                place[1]=10 * math.floor(place[1]/10)
                place[2]=10 * math.floor(place[2]/10)
                cmds.move(place[0],place[1],place[2],"block"+str(self.blockIndex), r=True)
                cmds.move(place[0],place[1],place[2],"collisionBox"+str(self.blockIndex), r=True)
                
                
        if self.blockIndex==-1: #UI - desired amount
            self.generateRoots()
        
    def appendBlocks(self,amount=30,tag=None):
        
        while(amount>0):
            print("Amount",amount)
            self.spawnBlock(tag)
            blockName="block"+str(self.blockIndex)
            collisionName="collisionBox"+str(self.blockIndex)
            localInputConnectors=self.blockConnectors[blockName+"input"]
            localOutputConnectors=self.blockConnectors[blockName+"output"]
                        
            worked=False
            #Find Input - Output Combo - exhaustively
            inputOutputCombos=[]
            for localInput in localInputConnectors:
                for outsideOutput in self.outputConnectorList:
                    if not outsideOutput in localOutputConnectors:
                        inputOutputCombos.append([localInput,outsideOutput])
            random.shuffle(inputOutputCombos)
            
            rotationAmount=random.choice([0,90,180,270])
            cmds.rotate(0,rotationAmount,0,blockName,r=True)
            cmds.rotate(0,rotationAmount,0,collisionName,r=True)             
            
            tries=50 #if not found within the first 50 combinations, well tough luck
            for combo in inputOutputCombos:
                if worked:
                    continue
                if tries<=0:
                    continue
                for rotation in range(4):
                    if worked:
                        continue
                    if tries<=0:
                        break;
                    #Rotation
                    cmds.rotate(0,90,0,blockName,r=True)
                    cmds.rotate(0,90,0,collisionName,r=True)
                    
                    #Move
                    input=combo[0]
                    output=combo[1]
                    outputAbsPos=cmds.xform(output,q=True, t=True, ws=True)
                    outputRelPos=cmds.xform(output,q=True, t=True, r=True)
                    inputRelPos=cmds.xform(input,q=True, t=True, r=True)
                    inputAbsPos=cmds.xform(input,q=True, t=True, ws=True)
                    place=[0,0,0]
                    for coor in range(3):
                        place[coor]=outputAbsPos[coor]-inputAbsPos[coor]
                    cmds.move(place[0],place[1],place[2],blockName, r=True)
                    cmds.move(place[0],place[1],place[2],collisionName, r=True)
                    
                    
                    #Detect Collision
                    collided=False
                    for union in self.collisionUnions:
                        if detectCollision(union,collisionName):
                            collided=True
                            break
                    if collided==False:
                        collided=detectCollision("bedrock",collisionName)
                    print('_')
                    tries-=1
                    
                    if collided==False:
                       worked=True
                       break
                        
            if worked:                
                 #Add the block
                self.blockList.append(blockName)
                self.addToCollisionUnion(collisionName)               
                amount-=1
                
                #Refresh Viewport
                if self.blockIndex%10==0:
                    cmds.refresh()
                
                #Remove used inputs
                if input in self.inputConnectorList:
                    self.inputConnectorList.remove(input)
                if output in self.outputConnectorList:
                    self.outputConnectorList.remove(output)
                    
                #Remove all other coinciding inputs/outputs
                to_remove=[]
                for conn in localInputConnectors + localOutputConnectors:
                    for conn2 in self.inputConnectorList + self.outputConnectorList:
                        if (not conn2 in localInputConnectors + localOutputConnectors):
                            pos1 = cmds.xform(conn,q=True, t=True, ws=True)
                            pos2 = cmds.xform(conn2,q=True, t=True, ws=True)
                            if pos1==pos2:
                                to_remove.append(conn)
                                to_remove.append(conn2)
                for conn in to_remove:
                    if conn in self.inputConnectorList:
                        self.inputConnectorList.remove(conn)
                    if conn in self.outputConnectorList:
                        self.outputConnectorList.remove(conn)
                               
                                
                                    
                #TODO remove other touching inputs/outputs
                print('Worked!')
            else:
                for conn in localInputConnectors:
                    self.inputConnectorList.remove(conn)
                    cmds.delete(conn)
                for conn in localOutputConnectors:
                    self.outputConnectorList.remove(conn)
                    cmds.delete(conn)
                cmds.delete(blockName)
                print("Maximum tries for generation reached")
            
    def stairMaking(self,amount=4):
        worked=False
        
        for conn2 in self.inputConnectorList + self.outputConnectorList:
            for conn in self.outputConnectorList:
                if worked:
                    amount-=1
                    if amount<=0:
                        return                   
                
                worked=False
                
                if (not cmds.objExists(conn)) or (not cmds.objExists(conn2)):
                    continue
                
                pos1 = cmds.xform(conn,q=True, t=True, ws=True)
                pos2 = cmds.xform(conn2,q=True, t=True, ws=True)
                isProperHeight = pos2[1]==pos1[1]+5
                isProperHorizontal=(abs(pos1[0]-pos2[0])==5 and abs(pos1[2]-pos2[2])==0) or (abs(pos1[0]-pos2[0])==0 and abs(pos1[2]-pos2[2])==5)
                sameParent = cmds.listRelatives(conn,parent=True) == cmds.listRelatives(conn2,parent=True)
                if isProperHeight and isProperHorizontal and not sameParent:            
                    self.spawnBlock(tag="stairs")
                    blockName="block"+str(self.blockIndex)
                    collisionName="collisionBox"+str(self.blockIndex)
                        
                    angle=None
                    if pos1[2]-pos2[2]==5:
                        angle=180
                    elif pos1[2]-pos2[2]==-5:
                        angle=0
                    elif pos1[0]-pos2[0]==5:
                        angle=270
                    else:
                        angle=90
                    
                                  
                    cmds.rotate(0,angle,0,blockName,r=True)
                    cmds.rotate(0,angle,0,collisionName,r=True)
                   
                    #Move
                    localInput=self.blockConnectors[blockName+"input"][0]
                    localInputPos=cmds.xform(localInput,q=True, t=True, ws=True)
                    place=[0,0,0]
                    for coor in range(3):
                        place[coor]=pos1[coor]-localInputPos[coor]
                    cmds.move(place[0],place[1],place[2],blockName, r=True)
                    cmds.move(place[0],place[1],place[2],collisionName, r=True)
                    
                    
                    #Detect Collision
                    collided=False
                    for union in self.collisionUnions:
                        if detectCollision(union,collisionName):
                            collided=True
                            break
                    if collided==False:
                        collided=detectCollision("bedrock",collisionName)
                        
                    if collided==False:
                       worked=True
                    else:
                        cmds.delete(blockName)
                        
    def pillarMaking(self):            
        for pillar in self.pillarList: #find pillar position
            if cmds.objExists(pillar):
                for height in range(1,10): #make pillars all the way down
                    pillarPos=cmds.xform(pillar,q=True, t=True, ws=True)
                    pillarPos[1]-=10*height
                    
                    if pillarPos[1]<-20:
                        break
                    
                    self.spawnProp(tag="pillar")
                    pillarName="prop"+str(self.propIndex)
                    cmds.move(pillarPos[0]-5,pillarPos[1],pillarPos[2]-5,pillarName)
                    
                    collided=False
                    for union in self.collisionUnions:
                        if detectCollision(union,pillarName):
                            collided=True
                            break
                    if collided==False:
                        collided=detectCollision("bedrock",pillarName)
                        
                    if collided:
                        cmds.delete(pillarName)
                        break
            
    def propMaking(self):
        for propConn in self.propConnectors:
            if cmds.objExists(propConn):
                if self.propProperties[propConn][1] >= random.random(): #if the chance happens
                    pos=cmds.xform(propConn,q=True, t=True, ws=True)
                    
                    self.spawnProp(self.propProperties[propConn][0])
                    propName="prop"+str(self.propIndex)
                    cmds.move(pos[0]-5,pos[1],pos[2]-5,propName)
                    
                    collided=False
                    for union in self.collisionUnions:
                        if detectCollision(union,propName):
                            collided=True
                            break
                    if collided==False:
                        collided=detectCollision("bedrock",propName)
                        
                    if collided:
                        cmds.delete(propName)
            
    def generate(self):
        #Generate Roots
        self.generateRoots()        
        cmds.refresh()
        
        #Create the initial universal collision box
        for i in range(self.blockIndex+1):
             self.addToCollisionUnion("collisionBox"+str(i))                    
        
        #Append Blocks
        self.appendBlocks(amount=self.baseAmount,tag="base")        
        cmds.refresh()
        
        self.appendBlocks(amount=self.structureAmount,tag="infrastructure")        
        cmds.refresh()
        
        self.stairMaking(amount=self.structureAmount/2)        
        cmds.refresh()
        
        self.pillarMaking()
        cmds.refresh()
        
        self.propMaking()
        
        #Remove collision blocks
        for union in self.collisionUnions:
            cmds.delete(union)
        for coll in self.collisionBoxes.values():
            if cmds.objExists(coll):
                cmds.delete(coll)
        #Remove connectors
        for conn in self.inputConnectorList+self.outputConnectorList:
            if cmds.objExists(conn):
                cmds.delete(conn)
        for conn in self.pillarList:
            if cmds.objExists(conn):
                cmds.delete(conn)
        for conn in self.propConnectors:
            if cmds.objExists(conn):
                cmds.delete(conn)
        #Remove bedrock
        cmds.delete("bedrock")
                    
#---------------------------------------------------------------------------

class UI(object):
    def __init__(self):
        self.mainWindow = cmds.window(w=420,h=100)
        cmds.showWindow(self.mainWindow)
        self.column=cmds.columnLayout()
            
        cmds.rowLayout(nc=8,p=self.column)
        cmds.text(label="Seed")    
        self.textF=cmds.textField(cc=partial(self.setSeed))
        cmds.rowLayout(nc=8,p=self.column)
        self.randomizeButton=cmds.button("Randomize", align="left",c=partial(self.randomize))
        
        cmds.rowLayout(nc=8,p=self.column)
        cmds.text(label="Root Chance Deviation")
        self.amountRoots=cmds.floatField("Base Blocks",minValue=0.5,maxValue=2.0, value=1.0) 
        cmds.rowLayout(nc=8,p=self.column)
        cmds.text(label="First Layer Amount")
        self.amountBase=cmds.intField("Base Blocks",cc=partial(self.setMaxAmountBase),minValue=5, value=15)        
        cmds.rowLayout(nc=8,p=self.column)
        cmds.text(label="Second Layer Amount")
        self.amountStructure=cmds.intField("Structures",cc=partial(self.setMaxAmountSecondBase),minValue=5, value=15)
        cmds.rowLayout(nc=8,p=self.column)
        cmds.text(label="Maximum Distance from Center")
        self.amountDistance=cmds.intField("Distance",minValue=100, maxValue=200, value=200)
        cmds.rowLayout(nc=8,p=self.column)
        self.generateButton=cmds.button("Generate", align="left",c=partial(self.generate))
        
        self.randomize()
    
    def randomize(self,*args):
        generateSeed()
        newSeed=str(random.random()*1000)
        cmds.textField(self.textF, e=True, text=newSeed)
        generateSeed(newSeed)
        getVertexList()
    
    def generate(self,*args):
        deleteAll()
        DG=DungeonGenerator()
        DG.baseAmount=cmds.intField(self.amountBase,q=True,value=True)
        DG.structureAmount=cmds.intField(self.amountStructure,q=True,value=True)
        DG.distanceAmount=cmds.intField(self.amountDistance, q=True, value=True)
        DG.rootsAmount=cmds.floatField(self.amountRoots, q=True, value=True)
        DG.generate()
        currentSeed=cmds.textField(self.textF, q=True, text=True)
        cmds.textField(self.textF, e=True, text=currentSeed)
        
    def setSeed(self,*args):
        newSeed=cmds.textField(self.textF, q=True, text=True)
        generateSeed(newSeed)
        getVertexList()
        
    def setMaxAmountBase(self,*args):
        dangerValue=cmds.intField(self.amountBase,q=True,value=True)
        if dangerValue>30:
            cmds.confirmDialog(message='Are you sure? Going above 30 may take a while.')
            
    def setMaxAmountSecondBase(self,*args):
        dangerValue=cmds.intField(self.amountStructure,q=True,value=True)
        if dangerValue>30:
            cmds.confirmDialog(message='Are you sure? Going above 30 may take a while.')
       
       
ui=UI()


