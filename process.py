'''
Created on Jan 11, 2015

@author: zhaohengyang
'''
import os,sys,shutil
import zipfile
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os,re
from subprocess import *
import os,re
import shutil
import subprocess
import variables
from time import clock

class ClassNode(object):

    
    def getClassPath(self):
        return self.classPath
    
    def getClassName(self):
        return self.className
    
    def getClassFullName(self):
        return self.classFullName

    def getClassType(self):
        return self.classType
    
    def getInvokeMethodList(self):
        return self.invokeMethodList
    
    
    def __init__(self, path, name):
        self.classPath = path
        self.className = name


        self.classFullName = ""
        self.classType = "other"
        self.invokeMethodList = []
        self.initialize(path)
    
    def updateType(self, cType):
        # First type found which means classType is still in default value("other"):
        if cType == "other":
            return
        
        #print "update:" + self.className + " from:" + self.classType + " to: " + cType
        if self.classType == "other":
            self.classType = cType
        
        else:
            typeList = cType.split(",") #cType can be "activity,service"
            for typeItem in typeList:
                # Found type is not exist, add type to it
                if self.classType.find(typeItem) == -1:
                    self.classType = self.classType + "," + typeItem

    def checkFirstTwoLine(self, filePath):
        smaliFile = open(filePath,'r')
        firstLine = smaliFile.readline()
        
        firstLine = firstLine.split(" ")[-1]
        self.classFullName = firstLine[:-2]
        #print "classFullName:" + self.classFullName
        secondLine = smaliFile.readline()
        #print  self.className + ": " + secondLine
        
        if secondLine == ".super Landroid/app/Activity;\n":
            #print "update activity"
            self.updateType("activity")
        elif secondLine == ".super Landroid/app/Service;\n":
            self.updateType("service")
        elif secondLine == ".super Landroid/content/BroadcastReceiver;\n":
            self.updateType("receiver")
        elif secondLine == ".super Landroid/content/ContentProvider;\n":
            self.updateType("provider")
        smaliFile.close()
    
     
    # Extract essential APIs from smali files
    def initialize(self, filePath):
        # initialize class full name and class type
        self.checkFirstTwoLine(filePath)
        
        # initialize invokelist
        smaliFile = open(filePath,'r')       
        for line in smaliFile:
            #print line
                   
            if re.search(r'^ *invoke', line):
                #print "line:"+ line
                if line.find(";->") != -1 :
                    className,methodName = line.split(";->")
                else:
                    continue
                temp,className = className.split("}, ")
                #if className.find("$") != -1 :
                #    tempList = className.split("$")
                #    className = tempList[0]
                methodName,temp = methodName.split("(")
                methodName = methodName + "()"
                systemCall = className + '->' + methodName
                #print systemCall
                
                self.invokeMethodList.append(systemCall)
                   
        smaliFile.close()
    
    
    def serizalize(self, outputPath):
        outputFile = open(outputPath,'a')
        outputFile.write(self.classType + "\t\t" + self.className + "\n")
        
    
        
class Sample():

    
    def __init__(self, path):
        self.smali_exist = False
        self.samplePath = ""
        self.manifestPath = path + '/' + 'AndroidManifest.xml'
        self.ClassNodeList = []
        self.smali = []
        self.smali_classification = []
        self.startPointNum = 0
        self.finishedClassInOneRound = [] # Each note can only been visit once in one round
        self.decode_apk(path)
        self.mark()

    def decode_apk(self, path):
		out_folder = path[:-4]
		apk_name = out_folder.split('/')[-1]
		out_folder = out_folder.replace(apk_name, "")
		out_folder = out_folder[:-5]
		out_folder = variables.decoded_apk_dir + apk_name
		decode_cmd = "./apktool.sh d --quiet -o '" + out_folder + "' '" + path + "'"
		decode_subp = subprocess.Popen(['/bin/sh', '-c', decode_cmd], stdout=subprocess.PIPE)
		out = decode_subp.communicate()[0]
		self.samplePath = out_folder
		#./apktool.sh d -f -o /Users/rschmicker/Documents/SURF/apks/Facebook /Users/rschmicker/Documents/SURF/apks/Facebook.apk
        
        
    def listClassPath(self, sampledir):
        classPathList = []
        for root,dirs,files in os.walk(sampledir):
            for filespath in files:           
                fullPath = os.path.join(root,filespath)
                if re.search(r'.smali$', fullPath):
                    classPathList.append(fullPath) 
        return classPathList
    
    def getClassNodeIndex(self, classFullName):
        for index in range(0, len(self.ClassNodeList)):
            if self.ClassNodeList[index].getClassFullName() == classFullName:
                return index
        
    def initialize(self):
        classPathList = self.listClassPath(self.samplePath)
        # Load all smali file into class node,
        for classPath in classPathList:
            filePathNoExt = os.path.splitext(classPath)[0]
            className = os.path.basename(filePathNoExt)
            self.ClassNodeList.append(ClassNode(classPath, className))

        checkNum = 0
        # Put four types of class node to the top of the list
        for classNode in self.ClassNodeList:
            if classNode.getClassType() != "other":
                checkNum += 1
                self.ClassNodeList.insert(0, self.ClassNodeList.pop(self.ClassNodeList.index(classNode)))
        self.startPointNum = checkNum
        
    
    def update(self, currentNode, classFullNameList, type):  
        children = []
        currentNode.updateType(type)
        if currentNode.getClassFullName() not in self.finishedClassInOneRound:
            self.finishedClassInOneRound.append(currentNode.getClassFullName()) # Each note can only been visit once in one round
        
        #print "go down! current node:" + str(self.ClassNodeList.index(currentNode)) + "\t" + currentNode.getClassName()
        #print "current node:" + currentNode.getClassFullName()
        #print self.finishedClassInOneRound
        for invokeFullName in currentNode.getInvokeMethodList(): # check all possible invoke class
            invokeClassFullName = invokeFullName.split("->")[0]
            # if the invoke class can be found in the class node list
            # also, the class node havn't been visited, then, save for later visit
            if invokeClassFullName in classFullNameList:
                #print "invokeClassFullName: " + invokeClassFullName
                index = self.getClassNodeIndex(invokeClassFullName)
                #print "index: " + str(index)
                children.append(index)
        
            
        
        # Go visit all the node
        for index in children:
            if self.ClassNodeList[index].getClassFullName() not in self.finishedClassInOneRound:
                self.update(self.ClassNodeList[index], classFullNameList, type)
            #print children
            
        #print "go up!" + "current node:" + str(self.ClassNodeList.index(currentNode)) + "\t" + currentNode.getClassName()
        
    def mark(self):
        # initialize
        self.initialize()  
        # Create a name list from class node list
        classFullNameList = []
        for classNode in self.ClassNodeList:
            classFullNameList.append(classNode.getClassFullName())
            self.smali.append(classNode.className)
            self.smali_classification.append(classNode.classType)
            #print(classNode.classType + "\t\t" + classNode.className) #HURRR
            
        # Update each class node, only search from each start points
        #for index in range(0, self.startPointNum):
        #    self.update(self.ClassNodeList[index], classFullNameList, self.ClassNodeList[index].getClassType())
        #   self.finishedClassInOneRound = [] 
            #print "currentRound: " + str(index)

        # Update each sub-classes
        #for index in range(0,len(self.ClassNodeList)):
        #    name = self.ClassNodeList[index].getClassName()
        #    if name.find("$") != -1:
        #        name = name.split("$")[0]
            
        #    for node in self.ClassNodeList:
        #        if node.getClassName() == name:
        #            self.ClassNodeList[index].updateType(node.getClassType())
                    #print self.ClassNodeList[index].getClassName() + " " + self.ClassNodeList[index].getClassType()
        if len(self.smali) != 0:
            self.smali_exist = True

    def outputPrecentageOfMark(self, outputPath):
        totalNum = len(self.ClassNodeList)
        uncovered = 0
        for classN in self.ClassNodeList: 
            if classN.getClassType() == "other":
                uncovered += 1
        if totalNum > 0:
            print "percentageOfMarK: " + str(float(totalNum - uncovered)/float(totalNum))
            outputFile = open(outputPath, "a")
            outputFile.write(str(float(totalNum - uncovered)/float(totalNum)) + "\n") 
        else:
            print "percentageOfMarK: 1"
            outputFile = open(outputPath, "a")
            outputFile.write("1\n")        
        
    def serizalize(self, outputPath):
        for classNode in self.ClassNodeList:
            print classNode.getClassType()
            classNode.serizalize(outputPath)
         
    def proceesEachClass(self):
        #print "Sample::processEachClass"
        vectorDic = {}
        for classNode in self.ClassNodeList:
            typeList = classNode.getClassType().split(",") # parse class type
            for eachType in typeList:
                for invokeMethod in classNode.getInvokeMethodList():
                    if invokeMethod not in vectorDic.keys():
                        vectorDic[invokeMethod] = [0,0,0,0,0]
                    if eachType == "activity":
                        vectorDic[invokeMethod][0] = 1
                    elif eachType == "service":
                        vectorDic[invokeMethod][1] = 1
                    elif eachType == "provider":                
                        vectorDic[invokeMethod][2] = 1
                    elif eachType == "receiver":
                        vectorDic[invokeMethod][3] = 1
                    elif eachType == "other":
                        vectorDic[invokeMethod][4] = 1
                        
        return vectorDic
            
   
            
    # Extract features from the invoke list, update featurelist3 and featurelist4 in feature table        
    def extractFeatureFromAPIs(self, vectorDic, featureTable):
        #print "extractFeatureFromAPIs start:"
        for functionName in vectorDic.keys():     
            value = vectorDic[functionName][0] + 2 * vectorDic[functionName][1] + \
                4 * vectorDic[functionName][2] + 8 * vectorDic[functionName][3] 
            #print [functionName, vectorDic[functionName],value]
            if functionName in featureTable.featureList.keys():
                #print "found!!!!!"
                featureTable.featureList[functionName] = value
            
    
#sample = Sample("/Users/rschmicker/Documents/SURF/apks/sample.apk")
#sample = Sample("./Facebook")
#sample.mark()    
#sample.serizalize("./output.txt")


