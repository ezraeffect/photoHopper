import datetime
import logging
import os
import re
import subprocess
import sys
import shutil

import rawpy

from systemTheme import getSysTheme

from PyQt6.QtCore import Qt, QModelIndex, QThread, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPixmap, QFont, QBrush, QColor, QImage
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QButtonGroup, QPushButton, QLineEdit,
    QTableView, QMessageBox, QHeaderView, QLabel, QComboBox, QProgressBar, QRadioButton,
    QSpacerItem, QSizePolicy, QGraphicsView, QGraphicsScene, QFileDialog
)

from exiftool import ExifToolHelper

"""
TODO
- 노츨 3요소 가운데 정렬
- 렌즈 제조사도 추가
- 미리보기 세로 사진 돌아가는 버그
"""
class FileCategorizer(QThread):
    progressChanged = pyqtSignal(int, int, str)
    finished = pyqtSignal()
    errorOccurred = pyqtSignal(str)
    setRowColor = pyqtSignal(int, int, int)

    def __init__(self, window, totalRowNum, copyOptionList):
        super().__init__()
        self.window = window
        self.totalRowNum = totalRowNum
        self.copyOptionList = copyOptionList



    def run(self):
        trueCount = 0
        progressCount = 0

        # 정리해야할 파일 갯수 카운트
        for row in range(self.totalRowNum):
            if self.window.getChecked(row, 0):
                trueCount += 1
        # 파일 정리 작업
        for row in range(self.totalRowNum):
            if self.window.getChecked(row, 0):
                originPath = self.window.getItem(row, 3)
                destPath = self.window.getItem(row, 4)
                destDir = os.path.dirname(destPath)
                destName = os.path.basename(destPath)

                self.progressChanged.emit(progressCount, trueCount, destName)


                try:
                    if not os.path.exists(destDir):
                        os.makedirs(destDir)
                    if os.path.exists(destPath): #  중복 경로인 경우 무조건 삭제 (덮어씌기)
                        os.remove(destPath)
                    if self.copyOptionList == 1:
                        shutil.copy2(originPath, destPath)
                    elif self.copyOptionList == 2:
                        shutil.move(originPath, destPath)

                    progressCount += 1

                    self.progressChanged.emit(progressCount, trueCount, destName)

                    if getSysTheme() == 1: #  시스템 테마가 다크모드면
                        colorCode = 1
                    else:
                        colorCode = 3
                    self.setRowColor.emit(colorCode, row, 1)

                except Exception as e:
                    if getSysTheme() == 1: #  시스템 테마가 다크모드면
                        colorCode = 0
                    else:
                        colorCode = 2
                    self.setRowColor.emit(colorCode, row, 1)
                    self.errorOccurred.emit(str(e))
                    return

        self.finished.emit()
class SearchWorker(QThread):
    progressChanged = pyqtSignal(int, int, str)  # 현재 진행, 총 진행
    searchCompleted = pyqtSignal(list)
    errorOccurred = pyqtSignal(str)

    def __init__(self, path, typeList, dest_path, searchOption, dataFormat):
        super().__init__()
        self.path = path
        self.typeList = typeList
        self.dest_path = dest_path
        self.searchOption = searchOption
        self.dataFormat = dataFormat

    def addSymbol(self, value, type):
        if value == 'NA':
            return 'NA'
        else:
            if type == 'focal':
                return str(value) + 'mm'
            elif type == 'fNum':
                return 'f/' + str(value)
            elif type == 'exposure':
                if value >= 1:
                    return f"{int(value)}\""
                else:
                    denominator = int(1 / value) if value != 0 else 1
                    return f"1/{denominator}"

    def cleanSymbol(self, value):
        invalid_chars = r'[\/:?\*"<>\|]'
        invalid_names = r'^\s|\s$|^\.'
        reserved_words = ['CON', 'AVX', 'NUL', 'PRN']

        value = re.sub(invalid_chars, '', value)
        value = re.sub(invalid_names, '', value)

        if value.upper() in reserved_words:
            value = ''

        return value

    def run(self):

        try:
            path, type, dest_path, searchOption, dateFormat = self.path, self.typeList, self.dest_path, self.searchOption, self.dataFormat
            print(dateFormat)
            i = 0
            formatStr1 = '%Y:%m:%d %H:%M:%S'
            formatStr2 = '%d/%m/%Y %H:%M'
            finalDict = []
            initialOrder = []
            allowedExt = ['.3fr', '.arq', '.arw', '.cr2', '.cr3', '.crm', '.crw', '.ciff', '.gpr', '.insp', '.jpeg', '.jpg',
                          '.mef', '.mrw', '.nef', '.nrw', '.pef', '.raf', '.raw', '.rw2', '.rwl', '.sr2', '.srf', '.srw',
                          '.webp', '.x3f', '.heic', '.heif', '.hif']

            if searchOption == 1:
                for file in os.listdir(path):
                    filePath = os.path.join(path, file)
                    if os.path.isfile(filePath) and any(filePath.lower().endswith(ext) for ext in allowedExt):
                        initialOrder.append(filePath)
            elif searchOption == 2:
                for (root, directories, files) in os.walk(path):
                    for file in files:
                        filePath = os.path.join(root, file)
                        if any(filePath.lower().endswith(ext) for ext in allowedExt):
                            initialOrder.append(filePath)

            if not initialOrder:
                self.errorOccurred.emit('빈 폴더이거나 사진을 찾지 못한 것 같습니다.')
                return



            with ExifToolHelper() as et:
                for tag in et.get_tags(initialOrder, tags=None):
                    exifDate = str(tag.get('EXIF:DateTimeOriginal', 'NA'))
                    fileDate = tag.get('File:FileCreateDate', 'NA')
                    fileName = os.path.basename(initialOrder[i])
                    fileDir = initialOrder[i]
                    bodyMake = tag.get('EXIF:Make', 'NA')
                    bodyModel = tag.get('EXIF:Model', 'NA')
                    focalLength = tag.get('EXIF:FocalLength', 'NA')
                    fNumber = tag.get('EXIF:FNumber', 'NA')
                    ISO = tag.get('EXIF:ISO', 'NA')
                    ExposureTime = tag.get('EXIF:ExposureTime', 'NA')
                    LensModel = tag.get('EXIF:LensModel', 'NA')

                    if (exifDate == 'NA') and (fileDate == 'NA'):
                        for t in tag.keys():
                            print(f"Key: {t}, value {tag[t]}")
                    else:
                        if ((exifDate == 'NA') or (exifDate == '0000:00:00 00:00:00')) and (fileDate != 'NA'):
                            exifDate = fileDate[0:19]
                        try:
                            exifDate = datetime.datetime.strptime(exifDate, formatStr1)
                            createDate = exifDate.strftime('%Y-%m-%d')
                        except ValueError as ve:
                            exifDate = datetime.datetime.strptime(exifDate, formatStr2)
                            createDate = exifDate.strftime('%Y-%m-%d')

                    if not dateFormat == "":
                        pathDate = exifDate.strftime(dateFormat)
                    elif dateFormat == "" and i == 0:
                        self.errorOccurred.emit('날짜 포맷을 입력하지 않아 기본값이 적용되었습니다.')
                        pathDate = createDate
                    else:
                        pathDate = createDate

                    if type == 0:
                        tempName = pathDate
                    elif type == 1:
                        tempName = self.addSymbol(focalLength, 'focal')
                    elif type == 2:
                        tempName = bodyMake + " " + bodyModel
                    elif type == 3:
                        tempName = LensModel
                    elif type == 4:
                        tempName = "unsupport"
                    elif type == 5:
                        tempName = "unsupport"
                    else:
                        tempName = "type_error"

                    cleanName = self.cleanSymbol(tempName)
                    destDir = os.path.join(dest_path, cleanName, fileName)

                    initialDict = {
                        "checked": True,
                        "fileName": fileName,
                        "createDate": createDate,
                        "originDir": fileDir,
                        "destDir": destDir,
                        "body": bodyMake + " " + bodyModel,
                        "focalLength": self.addSymbol(focalLength, 'focal'),
                        "fNumber": self.addSymbol(fNumber, 'fNum'),
                        "ISO": ISO,
                        "ExposureTime": self.addSymbol(ExposureTime, 'exposure'),
                        "lens": LensModel
                    }

                    finalDict.append(initialDict)
                    i += 1
                    self.progressChanged.emit(i + 1, len(initialOrder), fileName)

            self.searchCompleted.emit(finalDict)
        except Exception as e:
            self.errorOccurred.emit(str(e))

#################################
#       Main Window Class       #
#################################
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_index = None
        self.initUI()
        self.typeList = 0
        self.searchOptionList = 1   # 0 : None
                                    # 1 : Only root folder
                                    # 2 : including subfolders
        self.copyOptionList = 1     # 0 : None
                                    # 1 : Copy
                                    # 2 : Move
        self.isSearched = 0         # 0 : None
                                    # 1 : Yes
        self.fileCategorizer = None  # QThread 인스턴스를 저장할 변수
        self.searchWorker = None  # QThread 인스턴스를 저장할 변수

        # 로그 설정
        logging.basicConfig(filename='app.log', level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s: %(message)s')
    def initUI(self):
        self.setWindowTitle('photoHopper')
        self.setGeometry(100, 100, 1500, 1200)

        font = QFont()
        font.setBold(True)

        #################################
        #           Top Layout          #
        #################################

        layout = QVBoxLayout()

        pathLayout1 = QHBoxLayout()
        #  원본 경로 입력 박스
        self.pathTextBox = QLineEdit(self)
        self.pathTextBox.setPlaceholderText('정리할 폴더의 원본 경로를 입력하세요')
        pathLayout1.addWidget(self.pathTextBox)
        #  Dialog 호출 버튼
        self.dialogButton1 = QPushButton('...', self)
        self.dialogButton1.setMinimumSize(60, 10)
        pathLayout1.addWidget(self.dialogButton1)  # 수평 박스 레이아웃에 추가
        layout.addLayout(pathLayout1)


        pathLayout2 = QHBoxLayout()
        #  목적 경로 입력 박스
        self.destPathTextBox = QLineEdit(self)
        self.destPathTextBox.setPlaceholderText('사진을 옮길 목적 경로를 입력하세요')
        pathLayout2.addWidget(self.destPathTextBox)
        #  Dialog 호출 버튼
        self.dialogButton2 = QPushButton('...', self)
        self.dialogButton2.setMinimumSize(60, 10)
        pathLayout2.addWidget(self.dialogButton2)  # 수평 박스 레이아웃에 추가
        layout.addLayout(pathLayout2)

        #  라벨
        hbox = QHBoxLayout()
        explaneLabel1 = QLabel('분류 기준', self)
        explaneLabel1.setFont(font)
        hbox.addWidget(explaneLabel1)

        hbox.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        #  분류 기준 ComboBox
        self.combo_box = QComboBox()
        self.combo_box.addItem('날짜')
        self.combo_box.addItem('화각')
        self.combo_box.addItem('바디')
        self.combo_box.addItem('렌즈')
        self.combo_box.addItem('위치')
        self.combo_box.addItem('유사 이미지')
        hbox.addWidget(self.combo_box)

        hbox.addItem(QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        #  라벨
        explaneLabel2 = QLabel('미리 보기', self)
        explaneLabel2.setFont(font)
        hbox.addWidget(explaneLabel2)

        #  미리 보기 Button
        self.thumbnailToggleButton = QPushButton('OFF', self)
        self.thumbnailToggleButton.setMinimumSize(60, 10)
        hbox.addWidget(self.thumbnailToggleButton)

        hbox.addItem(QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        #  라벨
        explaneLabel3 = QLabel('검색 범위', self)
        explaneLabel3.setFont(font)
        hbox.addWidget(explaneLabel3)

        #  검색 범위 RadioButton
        self.radioButton1 = QRadioButton('해당 폴더만', self)
        self.radioButton2 = QRadioButton('모든 하위 폴더', self)
        self.radioGroup = QButtonGroup(self)
        self.radioGroup.addButton(self.radioButton1)
        self.radioGroup.addButton(self.radioButton2)
        self.radioButton1.setChecked(True)
        hbox.addWidget(self.radioButton1)
        hbox.addWidget(self.radioButton2)

        #  사진 검색 Button
        self.searchButton = QPushButton('검색', self)
        self.searchButton.setMinimumSize(60, 10)
        hbox.addWidget(self.searchButton)

        hbox.addItem(QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        #  라벨
        explaneLabel4 = QLabel('정리 방법', self)
        explaneLabel4.setFont(font)
        hbox.addWidget(explaneLabel4)

        #  정리 범위 RadioButton
        self.radioButton3 = QRadioButton('복사', self)
        self.radioButton4 = QRadioButton('이동', self)
        self.radioGroup2 = QButtonGroup(self)
        self.radioGroup2.addButton(self.radioButton3)
        self.radioGroup2.addButton(self.radioButton4)
        self.radioButton3.setChecked(True)

        hbox.addWidget(self.radioButton3)
        hbox.addWidget(self.radioButton4)

        #  정리 Button
        self.categorizeButton = QPushButton('정리', self)
        self.categorizeButton.setMinimumSize(60, 10)
        hbox.addWidget(self.categorizeButton)

        hbox.addItem(QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        #  날짜 포맷 TextBox
        explaneLabel5 = QLabel('날짜 포맷', self)
        explaneLabel5.setFont(font)
        hbox.addWidget(explaneLabel5)
        self.dateFormatTextBox = QLineEdit(self)
        self.dateFormatTextBox.setText('%Y%m%d')
        self.dateFormatTextBox.setPlaceholderText('%Y%m%d')
        hbox.addWidget(self.dateFormatTextBox)

        hbox.addItem(QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        explaneLabel6 = QLabel('필터', self)
        explaneLabel6.setFont(font)
        hbox.addWidget(explaneLabel6)

        self.fileFormatTextBox = QLineEdit(self)
        self.fileFormatTextBox.setPlaceholderText('검색어')
        hbox.addWidget(self.fileFormatTextBox)

        self.fileSelectButton = QPushButton('선택', self)
        self.fileSelectButton.setMinimumSize(60, 10)
        hbox.addWidget(self.fileSelectButton)

        self.fileUnselectButton = QPushButton('해제', self)
        self.fileUnselectButton.setMinimumSize(60, 10)
        hbox.addWidget(self.fileUnselectButton)

        self.allSelectButton = QPushButton('전체선택', self)
        self.allSelectButton.setMinimumSize(60, 10)
        hbox.addWidget(self.allSelectButton)

        self.allUnselectButton = QPushButton('전체해제', self)
        self.allUnselectButton.setMinimumSize(60, 10)
        hbox.addWidget(self.allUnselectButton)

        hbox.addStretch(1)
        layout.addLayout(hbox)

        #################################
        #           Mid Layout          #
        #################################
        mid_layout = QHBoxLayout()

        # 이미지를 표시할 QGraphicsView와 QGraphicsScene 생성
        self.graphicsView = QGraphicsView(self)
        self.graphicsView.setMaximumWidth(500)  # 가로 500px 고정
        self.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphicsView.hide()
        mid_layout.addWidget(self.graphicsView)

        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)

        # 테이블뷰 생성
        self.tableView = QTableView(self)
        self.model = QStandardItemModel()
        self.tableView.setModel(self.model)
        header = self.tableView.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tableView.setAlternatingRowColors(True)
        mid_layout.addWidget(self.tableView)

        layout.addLayout(mid_layout)

        #################################
        #          Bottom Layout        #
        #################################
        # TableView 하단에 텍스트 라벨 추가
        self.statusLabel = QLabel('상태 : 준비 완료', self)
        layout.addWidget(self.statusLabel)

        # 텍스트 라벨 하단에 프로그레스바 추가
        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)
        layout.addWidget(self.progressBar)

        #warnLabel = QLabel('파일의 손상, 삭제, 또는 기타 현상에 대한 책임은 사용자에게 있습니다.\nhttps://github.com/ezraeffect/photoHopper', self)
        #layout.addWidget(warnLabel)

        self.setLayout(layout)

        #################################
        #         Signal Process        #
        #################################
        # Radio Button Toggled
        self.radioButton1.toggled.connect(self.searchOptionBtnToggled)      # 해당 폴더만 검색
        self.radioButton2.toggled.connect(self.searchOptionBtnToggled)      # 모든 하위 폴더도 검색
        self.radioButton3.toggled.connect(self.copyOptionBtnToggled)        # 복사
        self.radioButton4.toggled.connect(self.copyOptionBtnToggled)        # 이동

        # ComboBox Text Changed
        self.combo_box.currentTextChanged.connect(self.comboboxChangeHandler)

        # TableView item Changed
        #self.model.itemChanged.connect(self.radioToggleHandler)           # TableView 셀에 내용이 변경된 경우

        # TableView Cell Clicked
        self.tableView.clicked.connect(self.openFileToClickCell)            # 원본 경로 셀 클릭시
        self.tableView.clicked.connect(self.showImageToClickCell)           # 파일명 셀 클릭시

        # Button Clicked
        self.thumbnailToggleButton.clicked.connect(self.toggleImageArea)    # 미리보기 버튼 클릭시
        self.searchButton.clicked.connect(self.searchFiles)                 # 파일찾기 버튼 클릭시
        self.categorizeButton.clicked.connect(self.categorizeFiles)         # 분류시작 버튼 클릭시
        self.dialogButton1.clicked.connect(lambda: self.showDialog(1))      # Dialog 버튼 클릭시
        self.dialogButton2.clicked.connect(lambda: self.showDialog(2))      # Dialog 버튼 클릭시
        self.fileSelectButton.clicked.connect(self.fileSelect)
        self.fileUnselectButton.clicked.connect(self.fileUnselect)
        self.allSelectButton.clicked.connect(self.allSelect)
        self.allUnselectButton.clicked.connect(self.allUnselect)

    def comboboxChangeHandler(self, text):
        #self.label.setText(f'selected item: {text}')
        if text == "날짜":
            self.typeList = 0
        elif text == "화각":
            self.typeList = 1
        elif text == "바디":
            self.typeList = 2
        elif text == "렌즈":
            self.typeList = 3
        elif text == "위치":
            self.typeList = 4
        elif text == "유사 이미지":
            self.typeList = 5
        else:
            self.typeList = 99
            return
        print(f'combobox changed to: {text}')
        self.statusLabel.setText(f'옵션 : {text}')
    def radioToggleHandler(self, item):
        if item.isEditable():
            row = item.row()
            column = item.column()
            new_value = item.text()
            print(f'Row {row}, Column {column} changed to: {new_value}')
    def searchFiles(self):
        self.progressBar.reset()
        path = self.pathTextBox.text()
        dest_path = self.destPathTextBox.text()
        typeList = self.typeList
        searchOption = self.searchOptionList
        dateFormat = self.dateFormatTextBox.text()

        if not (os.path.exists(path) and os.path.exists(dest_path)):
            QMessageBox.critical(self, '오류', '유효한 경로를 입력하세요.')
            return

        if searchOption == 0:
            QMessageBox.critical(self, '오류', '폴더 옵션을 선택해주세요.')
            return

        self.statusLabel.setText(f'진행 중 : 폴더에서 사진 목록을 가져옵니다')
        self.progressBar.reset()
        self.progressBar.setRange(0, 0)
        #self.startLongRunningTask()


        # QThread 사용하여 파일 검색 작업 수행
        self.searchWorker = SearchWorker(path, typeList, dest_path, searchOption, dateFormat)
        self.searchWorker.progressChanged.connect(self.updateProgress)
        self.searchWorker.searchCompleted.connect(self.onSearchCompleted)
        self.searchWorker.errorOccurred.connect(self.onSearchError)

        self.searchWorker.start()
    def onSearchCompleted(self, results):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['', '파일명', '촬영일', '원본 경로', '목적 경로', '카메라', '초점 거리',
                                              '조리개 값', 'ISO', '노출 시간', '렌즈'])

        for item in results:
            row = []
            check_item = QStandardItem()
            check_item.setCheckable(True)
            check_item.setCheckState(Qt.CheckState.Checked if item['checked'] else Qt.CheckState.Unchecked)
            row.append(check_item)
            row.append(QStandardItem(item['fileName']))
            row.append(QStandardItem(item['createDate']))
            row.append(QStandardItem(item['originDir']))
            row.append(QStandardItem(item['destDir']))
            row.append(QStandardItem(item['body']))
            row.append(QStandardItem(item['focalLength']))
            row.append(QStandardItem(item['fNumber']))
            row.append(QStandardItem(str(item['ISO'])))
            row.append(QStandardItem(item['ExposureTime']))
            row.append(QStandardItem(item['lens']))
            self.model.appendRow(row)

        for column in range(self.model.columnCount()):
            self.tableView.resizeColumnToContents(column)

        self.statusLabel.setText(f'완료 : 파일 검색을 완료했습니다.')
        self.isSearched = 1
    def onSearchError(self, error):
        QMessageBox.critical(self, '오류', error)
        self.statusLabel.setText(f'오류: {error}')
    def searchOptionBtnToggled(self):
        selected_button = self.radioGroup.checkedButton()
        if selected_button:
            selected_text = selected_button.text()
            print(f'Radio button changed to: {selected_text}')
            self.statusLabel.setText(f'옵션 : {selected_text}')
            if selected_text == '해당 폴더만':
                self.searchOptionList = 1
            elif selected_text == '모든 하위 폴더':
                self.searchOptionList = 2
            else:
                self.searchOptionList = 0
    def copyOptionBtnToggled(self):
        selected_button = self.radioGroup2.checkedButton()
        if selected_button:
            selected_text = selected_button.text()
            #print(f'Radio button changed to: {selected_text}')
            self.statusLabel.setText(f'옵션 : {selected_text}')
            if selected_text == '복사':
                self.copyOptionList = 1
            elif selected_text == '이동':
                self.copyOptionList = 2
            else:
                self.copyOptionList = 0
    def openFileToClickCell(self, index: QModelIndex):
        # 셀 클릭 시 파일 열기
        row = index.row()
        col = index.column()
        #print(f'row: {row} / col : {col}')
        if col == 3:
            item = self.model.item(row, col)
            file_path = item.text()
            print(file_path)
            if file_path is not None:
                if os.path.isfile(file_path):
                    # 파일 열기
                    if sys.platform == "win32":
                        os.startfile(file_path)
                    elif sys.platform == "darwin":
                        subprocess.call(["open", file_path])
                    else:
                        subprocess.call(["xdg-open", file_path])
    def showImageToClickCell(self, index: QModelIndex):
        # 셀 클릭 시 파일 열기
        row = index.row()
        col = index.column()
        if col == 1:
            item = self.model.item(row, col+2)
            file_path = item.text()
            #print(file_path)
            if file_path is not None:
                if os.path.isfile(file_path):
                    extension = os.path.splitext(file_path)[1]
                    if extension == '.jpg' or extension == '.JPG':
                        # 이미지를 QGraphicsScene에 추가하여 표시
                        pixmap = QPixmap(file_path)
                        if not pixmap.isNull():
                            pixmap = pixmap.scaledToWidth(500, Qt.TransformationMode.FastTransformation)
                            self.scene.clear()
                            self.scene.addPixmap(pixmap)
                    elif extension == '.heic' or extension == '.HEIC':
                        QMessageBox.warning(self, '경고', f'HEIC 파일은 미리보기가 지원되지 않습니다.')
                    else:
                        with rawpy.imread(file_path) as raw:
                            rgb = raw.postprocess()  # rawpy를 사용하여 RGB 이미지로 후처리

                        # RGB 이미지 데이터를 QImage로 변환
                        image_qt = QImage(rgb.data, rgb.shape[1], rgb.shape[0], QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(image_qt)
                        if not pixmap.isNull():
                            pixmap = pixmap.scaledToWidth(500, Qt.TransformationMode.FastTransformation)
                            self.scene.clear()
                            self.scene.addPixmap(pixmap)
    def toggleImageArea(self):
        if self.graphicsView.isVisible():
            self.graphicsView.hide()
            self.thumbnailToggleButton.setText("OFF")
        else:
            self.graphicsView.show()
            self.thumbnailToggleButton.setText("ON")
    def showDialog(self, num):
        folder_path = QFileDialog.getExistingDirectory(self, 'Select a folder')  # 폴더 선택 다이얼로그 표시

        if folder_path:
            if num == 1:
                self.pathTextBox.setText(folder_path)  # 선택된 폴더 경로를 텍스트 박스에 설정
            if num == 2:
                self.destPathTextBox.setText(folder_path)  # 선택된 폴더 경로를 텍스트 박스에 설정
    def getTableViewRow(self):
        return self.model.rowCount()
    def getTableViewCol(self):
        return self.model.columnCount()
    def getItem(self, row, col):
        item = self.model.item(row, col)
        if item is not None:
            return item.text()
    def getChecked(self,row, col):
        index = self.model.index(row, col)
        item = self.model.itemFromIndex(index)
        if item.checkState() == Qt.CheckState.Checked:
            check_states = True
        else:
            check_states = False
        return check_states
    def setRowBGcolor(self, row, color):
        for col in range(self.model.columnCount()):
            item = self.model.item(row, col)
            if item is not None:
                item.setBackground(QBrush(color))
    def categorizeFiles(self):
        # 초기 안내
        self.statusLabel.setText(f'진행 중 : 파일 정리를 준비 중 입니다.')

        self.progressBar.reset()
        self.progressBar.setRange(0, 0)

        # 오류 안내
        if self.isSearched == 0:
            QMessageBox.critical(self, '오류', '사진 검색을 먼저 실행해 주세요.')
            return
        elif self.copyOptionList == 0:
            QMessageBox.critical(self, '오류', '정리 방법을 선택해 주세요.')
            return

        # 1. 행 갯수 가져오기
        totalRowNum = self.getTableViewRow()  # 열 갯수

        # QThread 사용하여 파일 정리 작업 수행
        self.fileCategorizer = FileCategorizer(self, totalRowNum, self.copyOptionList)
        self.fileCategorizer.progressChanged.connect(self.updateProgress)
        self.fileCategorizer.finished.connect(self.onCategorizeFinished)
        self.fileCategorizer.errorOccurred.connect(self.onCategorizeError)
        self.fileCategorizer.setRowColor.connect(self.changeRowColor)
        self.fileCategorizer.start()
    def updateProgress(self, progressCount, trueCount, destName):
        self.statusLabel.setText(f'진행 중 : {progressCount}/{trueCount} - {destName}')
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(int((progressCount / trueCount) * 100))
    def onCategorizeFinished(self):
        self.statusLabel.setText(f'완료 : 파일 정리를 완료했습니다.')
        self.progressBar.setValue(100)
    def onCategorizeError(self, error):
        QMessageBox.critical(self, '오류', f'파일 정리 중 오류 발생: {error}')
        self.statusLabel.setText(f'오류 : {error}')
    def changeRowColor(self, colorCode, row, col):
        if colorCode == 0:  # Dark mode - Red
            color = QColor(213, 78, 72)
        elif colorCode == 1:  # Dark mode - Green
            color = QColor(0, 154, 99)
        elif colorCode == 2:  # Light mode - Red
            color = QColor(255, 124, 120)
        elif colorCode == 3:  # Light mode - Green
            color = QColor(82, 208, 156)
        else:
            color = QColor(0, 0, 0)

        item = self.model.item(row, col)
        if item is not None:
            item.setBackground(color)

    def fileSelect(self):
        fileFormat = self.fileFormatTextBox.text()
        if not fileFormat == "":
            countRow = self.getTableViewRow()
            for row in range(countRow):
                text = self.getItem(row, 1)
                if fileFormat in text:
                    item = QStandardItem()
                    item.setCheckState(Qt.CheckState.Checked)
                    self.model.setItem(row, 0, item)
        else:
            QMessageBox.critical(self, '오류', '검색어를 입력해주세요.')
    def fileUnselect(self):
        fileFormat = self.fileFormatTextBox.text()
        if not fileFormat == "":
            countRow = self.getTableViewRow()
            for row in range(countRow):
                text = self.getItem(row, 1)
                if fileFormat in text:
                    item = QStandardItem()
                    item.setCheckState(Qt.CheckState.Unchecked)
                    self.model.setItem(row, 0, item)
        else:
            QMessageBox.critical(self, '오류', '검색어를 입력해주세요.')
    def allSelect(self):
        countRow = self.getTableViewRow()
        for row in range(countRow):
                item = QStandardItem()
                item.setCheckState(Qt.CheckState.Checked)
                self.model.setItem(row, 0, item)
    def allUnselect(self):
        countRow = self.getTableViewRow()
        for row in range(countRow):
                item = QStandardItem()
                item.setCheckState(Qt.CheckState.Unchecked)
                self.model.setItem(row, 0, item)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())