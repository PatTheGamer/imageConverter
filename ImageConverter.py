'''
Created on Jan 11, 2012

@author: Ryan Moore
'''

import sys
import os
import re
import multiprocessing


from PySide.QtCore import *
from PySide.QtGui import *
from PIL import Image

from PIL import BmpImagePlugin,JpegImagePlugin,PngImagePlugin,TiffImagePlugin,GifImagePlugin

Image._initialized=2

class DragDropListWidget(QTreeWidget):
    dropped = Signal(list)
    def __init__(self,parent=None):
        QTreeWidget.__init__(self,parent)
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.setHeaderLabels(['Thumbnail','Image Name'])
        self.setColumnCount(2)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setLineWidth(3)
        self.setAcceptDrops(True)
        self.setIconSize(QSize(72,72))

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()
    
    def dragMoveEvent(self,event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self,event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
            l = []
            for url in event.mimeData().urls():
                l.append(str(url.toLocalFile()))
            self.dropped.emit(l)
        else:
            event.ignore()

class FileSelectTextBox(QWidget):
    
    def __init__(self):
        QWidget.__init__(self)
        self.textBox = QLineEdit()
        self.fileButton = QToolButton()
        self.fileButton.setAutoRaise(True)
        self.fileButton.setArrowType(Qt.UpArrow)
        self.fileButton.setMaximumWidth(self.textBox.height())
        self.fileButton.pressed.connect(self.launchFolderBrowser)
        self.mainLayout = QBoxLayout(QBoxLayout.LeftToRight)
        self.mainLayout.addWidget(self.textBox)
        self.mainLayout.addWidget(self.fileButton)
        self.setLayout(self.mainLayout)

    def launchFolderBrowser(self):
        self.fileButton.setDown(False)
        imageDirectory = QFileDialog.getExistingDirectory(self,"Select an Image Folder",os.path.expanduser('~'))
        self.textBox.setText(imageDirectory)
        
    def getFolderText(self):
        return self.textBox.text()
    
class BlockingQueue(QObject):
    def __init__(self,inputList):
        QObject.__init__(self)
        self.__inputList = inputList
        self.__listLen = len(self.__inputList)
        self.mutex = QMutex()
    def getNext(self):
        retVal = None #this will be used to kill threads that use this method.
        self.mutex.lock()
        
        if self.__listLen != 0:
            retVal = self.__inputList.pop()
            self.__listLen-=1             

        self.mutex.unlock()
        return retVal
    
class ImageConsumer(QThread):
    consumed = Signal()
    def __init__(self,blockingPictureList,directoryOption,targetDirectory,targetImageType):
        QThread.__init__(self)
        self.__directoryOption = directoryOption
        self.__targetDirectory = targetDirectory
        self.__targetImageType = targetImageType
        self.__blockingPicutreList = blockingPictureList
        self.__imageDictionary = {}
        self.__imageDictionary['jpeg'] = "JPEG"
        self.__imageDictionary['jpg'] = "JPEG"
        self.__imageDictionary['png'] = "PNG"
        self.__imageDictionary['tiff'] = "TIFF"
        self.__imageDictionary['tif'] = "TIFF"
        self.__running = True
        self.__runningMutex = QMutex()
    def setRunning(self,boolean):
        self.__runningMutex.lock()
        self.__running = boolean
        self.__runningMutex.unlock()
                
    def getRunning(self):
        self.__runningMutex.lock()
        retVal = self.__running
        self.__runningMutex.unlock()
        return retVal
         
    def run(self):
        while self.getRunning():
            nextUrl = self.__blockingPicutreList.getNext()
            if nextUrl == None:
                self.setRunning(False)
            else:
                self.consume(nextUrl)
            
    def consume(self,pictureUrl):
        #perform the image conversion here
        if pictureUrl == "":#This should never happen
            self.setRunning(False)
        else:
            outDirectory = ''
            if self.__directoryOption == "In place":
                outDirectory = os.path.dirname(pictureUrl)
            elif self.__directoryOption == "Single Directory":
                outDirectory = self.__targetDirectory
            else:
                pathListImage = getPathList(pictureUrl)
                pathListDirectory = getPathList(self.__targetDirectory)
                
                intersectIndex = 0
                while pathListImage[intersectIndex] == pathListDirectory[intersectIndex]:
                    intersectIndex+=1
                
                newDirectory = self.__targetDirectory
                pathLength = len(pathListImage)
                for index in xrange(intersectIndex,pathLength):
                    newDirectory = os.path.join(newDirectory,pathListImage[index])
                outDirectory=newDirectory

            if not os.path.exists(outDirectory):
                os.makedirs(outDirectory)   
                
            imageName = os.path.split(pictureUrl)[1]
            imageName = imageName[:imageName.rfind('.')]
                
            image = Image.open(pictureUrl)
            outputName = os.path.join(outDirectory,imageName)+'.'+self.__targetImageType
            image.save(outputName,self.__imageDictionary[self.__targetImageType])
            self.consumed.emit()                

def getPathList(path):
    pathToExpand = path
    if pathToExpand.find('.') != -1:
        pathToExpand = os.path.dirname(path)
    pathList = []
    while True:
        splitResult = os.path.split(pathToExpand)
        if splitResult[1] == "" or splitResult[0] == "":
            break
        else:
            pathList.insert(0, splitResult[1])
            pathToExpand = splitResult[0]
    return pathList

class AboutDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setWindowTitle("About")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Image Converter: Version 0.1"))
        layout.addWidget(QLabel("Copyright Ryan Moore 2012"))
        self.setLayout(layout)
        self.setFixedSize(450,100)

class MyMainWindow(QMainWindow):
    def __init__(self,app):
        QMainWindow.__init__(self)
        self.app = app
        mainLayoutWidget = QWidget()
        mainLayout = QBoxLayout(QBoxLayout.LeftToRight)
        
        leftLayout = QVBoxLayout()
        
        self.pictureListView = DragDropListWidget()
        self.pictureListView.dropped.connect(self.addPictures)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.iconListRightClick)
        
        leftLayout.addWidget(self.pictureListView)
        leftLayoutButtonLayout = QBoxLayout(QBoxLayout.LeftToRight)
        removeSelected = QPushButton("Remove Selected")
        removeSelected.pressed.connect(self.removeSelected)
        leftLayoutButtonLayout.addWidget(removeSelected)
        clearButton = QPushButton("Clear All Images")
        clearButton.pressed.connect(self.clearImages)
        leftLayoutButtonLayout.addWidget(clearButton)
        leftLayout.addLayout(leftLayoutButtonLayout)
        
        mainLayout.addLayout(leftLayout)
        groupBox = QGroupBox("Converter Settings")
        
        groupBoxLayout = QVBoxLayout()
        
        groupBoxFormLayout = QFormLayout()
        
        self.convertToComboBox = QComboBox()
        self.convertToComboBox.addItem("jpg")
        self.convertToComboBox.addItem("png")
        self.convertToComboBox.addItem("tif")
        self.convertToComboBox.setEditable(False)
        self.convertToComboBox.currentIndexChanged.connect(self.updateFileCountSlot)
        
        groupBoxFormLayout.addRow("Output type:",self.convertToComboBox)
        
        
        self.targetDirectoryComboBox = QComboBox()
        self.targetDirectoryComboBox.addItem("In place")
        self.targetDirectoryComboBox.addItem("Single Directory")
        self.targetDirectoryComboBox.addItem("New Directory Structure")
        self.targetDirectoryComboBox.setEditable(False)
        self.targetDirectoryComboBox.currentIndexChanged.connect(self.processTargetDirectorySettingChange)
        
        self.fileTextBox = FileSelectTextBox()
        self.fileTextBox.setEnabled(False)

        groupBoxFormLayout.addRow("Target Directory Settings:",self.targetDirectoryComboBox)
        groupBoxFormLayout.addRow("Target Directory:",self.fileTextBox)
        
        self.numFileCount=0
        self.numFiles = QLabel(str(self.numFileCount))
        groupBoxFormLayout.addRow("Number of files to be converted:",self.numFiles)
        
        
        groupBoxLayout.addLayout(groupBoxFormLayout)
        self.convertButton = QPushButton("Convert")
        self.convertButton.pressed.connect(self.convertImages)
        groupBoxLayout.addWidget(self.convertButton)
        
        groupBox.setLayout(groupBoxLayout)
        mainLayout.addWidget(groupBox)
        mainLayoutWidget.setLayout(mainLayout)
        self.__privateMainLayoutReference = mainLayoutWidget
        self.setCentralWidget(mainLayoutWidget)
        
        
        self.__initActions__()
        self.__initMenu__()
        self.__initToolbar__()
        
        self.__pictureUrlList = []
        self.__aboutDialog = None
        self.__progressBar = None
    
    def __initActions__(self):
        self.addDirectory = QAction(QIcon('icons/directory.png'),"Add Folder",self)
        self.addDirectory.setStatusTip("Add images from a folder.")
        self.addDirectory.triggered.connect(self.addDir)
        
        self.addPicture = QAction(QIcon('icons/text_directory.png'),"Add Image",self)
        self.addPicture.setStatusTip("Add an image.")
        self.addPicture.triggered.connect(self.addImage)
        
        self.exitAction = QAction("Exit",self)
        self.exitAction.setStatusTip("Exit")
        self.exitAction.setShortcut(QKeySequence.Close)
        self.exitAction.triggered.connect(self.close)
        
        self.aboutAction = QAction("About",self)
        self.aboutAction.setStatusTip("About Information")
        self.aboutAction.triggered.connect(self.showAbout)
        
    def __initMenu__(self):
        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction(self.addDirectory)
        fileMenu.addAction(self.addPicture)
        fileMenu.addAction(self.exitAction)
        
        helpMenu = self.menuBar().addMenu("&Help")
        helpMenu.addAction(self.aboutAction)

    def __initToolbar__(self):
        toolBar = self.addToolBar("Open Images")
        toolBar.addAction(self.addDirectory)
        toolBar.addAction(self.addPicture)

    def addPictures(self,pictureList):
        for url in pictureList:
            if os.path.exists(url) and self.__pictureUrlList.count(url)<1:
                icon = QIcon()
                icon.addPixmap(QPixmap(url),QIcon.Normal,QIcon.Off)
                item = QTreeWidgetItem(self.pictureListView)
                item.setText(1,os.path.basename(url))
                item.setStatusTip(1,url)
                item.setIcon(0,icon)
                self.__pictureUrlList.append(url)
        self.updateFileCount()

    def addDir(self):
        imageDirectory = QFileDialog.getExistingDirectory(self,"Select an Image Folder",os.path.expanduser('~'))
        if not ( imageDirectory == None or len(imageDirectory)==0):
            self.addPictures(self.__getPictureListFromDirectory(imageDirectory))
        else:
            self.statusBar().showMessage("A directory was not set by the file dialog.")
    
    @Slot(str)
    def processTargetDirectorySettingChange(self,message):
        if message == "In place" or message == 0:
            self.fileTextBox.setEnabled(False)
        else:
            self.fileTextBox.setEnabled(True)
    
    def addImage(self):
        image = QFileDialog.getOpenFileName(self,"Select an Image", os.path.expanduser('~'),"Image Files (*.png *.jpg *.jpeg *.tif *.tiff)")
        if not (image[0] == None or len(image[0])==0):
            self.addPictures([image[0]])
        else:
            self.statusBar().showMessage("An image file was not found or selected.")

    def clearImages(self):
        self.pictureListView.clear()
        self.__pictureUrlList = []
        self.updateFileCount()
        
    def removeSelected(self):
        selectedList = self.pictureListView.selectedItems()
        for selectedItem in selectedList:
            rowNumber = self.pictureListView.indexOfTopLevelItem(selectedItem)
            self.pictureListView.takeTopLevelItem(rowNumber)
            self.__pictureUrlList.pop(rowNumber)
        self.updateFileCount()
        
    def iconListRightClick(self,qpoint):
        globalPoint = self.mapToGlobal(qpoint)
        popupMenu = QMenu()
        popupMenu.addAction("Remove")
        
        selectedItem = popupMenu.exec_(globalPoint)
        if selectedItem:
            if selectedItem.iconText() == "Remove":
                selectedRow = self.pictureListView.indexOfTopLevelItem(self.pictureListView.currentItem())
                self.pictureListView.takeTopLevelItem(selectedRow)
                self.__pictureUrlList.pop(selectedRow)
        self.updateFileCount()
        
    def convertImages(self):
        if len(self.__pictureUrlList) == 0:
            return
        self.pictureList = []
        extensionPattern = re.compile("\." + self.convertToComboBox.currentText().strip() + "$")
        for url in self.__pictureUrlList:
            if extensionPattern.search(url) == None:
                self.pictureList.append(url)
        
        convertListLen = len(self.pictureList)
        
        if convertListLen == 0:
            return
        self.__progressBar = QProgressBar()
        self.__progressBar.setTextVisible(False)
        self.__progressBar.setRange(0,convertListLen)
        self.statusBar().insertPermanentWidget(1,self.__progressBar)
        self.progressCount = 0
      
        self.__privateMainLayoutReference.setEnabled(False)#disable the main ui while the convertion is going on.
            
        self.__consumerThreads = []
        self.__numActiveConsumerThreads = multiprocessing.cpu_count()
        self.__urlListForThreads = BlockingQueue(self.pictureList)
        for i in xrange(0,self.__numActiveConsumerThreads):
            
            consumer = ImageConsumer(self.__urlListForThreads,self.targetDirectoryComboBox.currentText(),self.fileTextBox.getFolderText(),self.convertToComboBox.currentText())
            consumer.consumed.connect(self.updateProgressBar)
            consumer.finished.connect(self.finishedConvert)            
            self.__consumerThreads.append(consumer)
        
        for thread in self.__consumerThreads:
            thread.start()

        
    def updateProgressBar(self):
        if self.__progressBar == None:
            return
        self.progressCount+=1
        self.__progressBar.setValue(self.progressCount)
        
    def finishedConvert(self):
        self.__numActiveConsumerThreads-=1
        if self.__numActiveConsumerThreads <=0:
            self.__privateMainLayoutReference.setEnabled(True)#reenable the main ui.
            self.__consumerThreads = None
            self.__urlListForThreads = None


            self.statusBar().removeWidget(self.__progressBar)
            self.__progressBar = None
        
    def updateFileCount(self):
        """
            This computes how many files will be converted based off of how many urls there are minus the number that share the conversion extension
        """
        fileCount = 0
        
        extensionPattern = re.compile("\." + self.convertToComboBox.currentText().strip() + "$")
        for url in self.__pictureUrlList:
            if extensionPattern.search(url) == None:
                fileCount+=1
        
        self.numFileCount = fileCount
        self.numFiles.setText(str(self.numFileCount))

    @Slot(int)
    def updateFileCountSlot(self,index):
        self.statusBar().showMessage("Output image type changed.")
        self.updateFileCount()

    def close(self):
        if self.__consumerThreads != None:
            for thread in self.__consumerThreads:
                thread.setRunning(False)
        self.app.quit()
        
    def closeEvent(self,event):
        event.accept()
        self.close()

    def __getPictureListFromDirectory(self,directory):
        pictureList = []
        imagePostfixPattern = re.compile("\.png|\.jpeg|\.jpg|\.tiff|\.tif")
        for (path,dirs,files) in os.walk(directory):
            for fileName in files:
                if imagePostfixPattern.search(fileName) != None:
                    pictureList.append(path+'/'+fileName)
        return pictureList

    def showAbout(self):
        if not self.__aboutDialog:
            self.__aboutDialog = AboutDialog()
        self.__aboutDialog.show()
        self.__aboutDialog.activateWindow()    

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MyMainWindow(app)
    mainWindow.show()
    app.exec_()
    sys.exit()