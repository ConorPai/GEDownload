#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2017/5/3 23:42
# @Author  : ZL
# @Site    : 
# @File    : GoogleHistoryMapTileRequest.py
# @Software: PyCharm
# Function:

import urllib
import urllib2
import math
from datetime import datetime
import sys
import os

class WebFileDownload:
    @staticmethod
    def SimpleDownload(url, filename):
        nRet = urllib.urlretrieve(url, filename)
        # print nRet

    @staticmethod
    def SimpleDownloadToBuffer(url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0', 'Cookie': 'SessionId=7SabEwADEAEAAQA4AOY3uMGdE6uggCa6luy5DMBTCRu5TZvx7cXYyC99QC0ANGkkbShqVHSxRq93/jTHTY1eZOInfzM=; State=1'}
            req = urllib2.Request(url=url, headers=headers)
            u = urllib2.urlopen(req, timeout=60)
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])
            buffer = u.read(file_size)
            return buffer
        except Exception, e:
            #print repr(e)
            return None

    @staticmethod
    def BigDownload(url, filename):
        headers = {'User-Agent':'GoogleEarth/7.1.8.3036(Windows;Microsoft Windows (6.2.9200.0);zh-Hans;kml:2.2;client:Free;type:default)'}
        req = urllib2.Request(url=url, headers=headers)
        u = urllib2.urlopen(req)
        f = open(filename, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        file_size_dl = 0
        block_sz = 8192#每次下载的大小
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break
            file_size_dl += len(buffer)
            f.write(buffer)
        f.close()

    @staticmethod
    def BreakDownload(url, filename):
        pass

class GoogleHistoryTileMapRequest:
    def __init__(self):
        self.ZeroTileGeoSize = 360
        self.ValidBoundRc = [-180.0, 180.0, 180.0, -180.0]#左右上下
        self.ValidLevelStart = 0
        self.ValidLevelEnd = 17
        self.ExpMinDoubleValue = pow(10, -20)

    def GetFromRange(self, rootUrl, boundRc, nlevelStart, nLevelEnd, dtTime, localRootDir):
        '''
        从一定范围获取影像
        :param rootUrl: 服务器根地址
        :param boundRc: 边界矩形范围(经纬度)，[左，右，上，下]
        :param nlevelStart: 起始瓦片级别（包含）
        :param nLevelEnd: 终止瓦片级别（包含）
        :param dtTime: 日期（datetime类型）
        :param localRootDir: 本地根地址
        :return:
        '''
        #首先判断是否有效范围
        if not self.__IsValidboundRc(boundRc):
            return False
        #判断是否有效层级
        if nLevelEnd > self.ValidLevelEnd:
            nLevelEnd = self.ValidLevelEnd
        if nlevelStart < self.ValidLevelStart:
            nlevelStart = self.ValidLevelStart
        if nlevelStart > nLevelEnd:
            return  False

        dtTimeInfoStr = self.__GetTimeInfoStrFormDatetime(dtTime)
        verStrSuc = {'i.157'}
        verStrOther = []
        errorCount = 0

        for i in range(1, 800):
            if i == 157 or i == 159:
                continue
            verStrOther.append('i.' + str(i))

        #秘钥内容
        SecretKeyContent = self.__GetSecretKeyContent()
        if None == SecretKeyContent:
            print 'can not get secret key content!'
            return False
        # usefulSKLen = 1024 #有效的秘钥长度

        #遍历每一层级瓦片进行下载。
        for nLevelIndex in range(nlevelStart, nLevelEnd+1):
            nTileGeoSize = self.__GetTileGeoSize(nLevelIndex)
            nColLeft = int(math.floor(float(boundRc[0]-self.ValidBoundRc[0])/nTileGeoSize))
            nColCount = int(math.ceil(float(boundRc[1]-boundRc[0]) / nTileGeoSize))
            nRowBottom = int(math.floor(float(boundRc[3]-self.ValidBoundRc[3]) / nTileGeoSize))
            nRowCount = int(math.ceil(float(boundRc[2] - boundRc[3]) / nTileGeoSize))
            #遍历所有行列号
            for rowIndex in range(nRowBottom, nRowBottom+nRowCount):
                for colIndex in range(nColLeft, nColLeft+nColCount):
                    dStartLon = colIndex * nTileGeoSize + self.ValidBoundRc[0]
                    dStartLat = rowIndex * nTileGeoSize + self.ValidBoundRc[3]
                    rowColInfoStr = self.__GetRowColInfoStr(dStartLat, dStartLon, nLevelIndex)

                    for verStr in verStrSuc:
                        tileUrl = rootUrl + '&f1-' + rowColInfoStr + '-' + verStr + '-' + dtTimeInfoStr
                        oriBuffer = WebFileDownload.SimpleDownloadToBuffer(tileUrl)
                        if oriBuffer is not None:
                            break

                    if oriBuffer is None:
                        print tileUrl
                        print '############'
                        errorCount += 1
                        continue
                    retBuffer = self.__DescryptPic(oriBuffer, SecretKeyContent)
                    if retBuffer is None:
                        continue
                    self.__SavePic(localRootDir, '{0}'.format(nLevelIndex), '{0}.jpg'.format(rowColInfoStr + '-' + verStr), retBuffer)
                    print 'yes'
                    continue

        print 'error count is ' + str(errorCount)
        return True

    def __IsValidboundRc(self, boundRc):
        '''
        判断边界矩形是否有效
        :param boundRc:
        :return:
        '''
        if boundRc[1] < self.ValidBoundRc[0] or \
                        boundRc[0] > self.ValidBoundRc[1] or \
                        boundRc[3] > self.ValidBoundRc[2] or \
                        boundRc[2] < self.ValidBoundRc[3] :
            return False
        return True

    def __IsValidLevel(self, nLevelIndex):
        '''
        判断是否为有效的层级
        :param nLevelIndex:
        :return:
        '''
        if nLevelIndex < self.ValidLevelStart or \
                nLevelIndex > self.ValidLevelEnd:
            return False
        return True

    def __GetTileGeoSize(self, nlevelIndex):
        '''
        获取指定级别瓦片的地理大小
        :param nlevel:
        :return:
        '''
        return self.ZeroTileGeoSize/math.pow( 2, nlevelIndex )

    def __GetRowColInfoStr(self, lat, lon, nLevel):
        '''
        获取行列字符串
        :param lat:
        :param lon:
        :return:
        '''
        strRowColInfo = ""
        for nLevelIndex in range(0, nLevel+1):
            nTileGeoSize = self.__GetTileGeoSize(nLevelIndex)
            nColIndex = int(math.floor(float(lon - self.ValidBoundRc[0]) / nTileGeoSize))
            nRowIndex = int(math.floor(float(lat - self.ValidBoundRc[3]) / nTileGeoSize))
            strRowColInfo = strRowColInfo + self.__GetRowColInfoChar(nRowIndex, nColIndex)
        return strRowColInfo

    def __GetRowColInfoChar(self, rowIndex, colIndex):
        '''
        获取指定级别下瓦片对于字符
        :param rowIndex:
        :param colIndex:
        :return:
        '''
        nRowLeft = rowIndex%2
        nColLeft = colIndex%2
        if nRowLeft > 0 and nColLeft > 0:
            return '2'
        elif nRowLeft > 0 and nColLeft == 0:
            return '3'
        elif nRowLeft == 0 and nColLeft == 0:
            return '0'
        else:
            return '1'

    def __GetTimeInfoStrFormDatetime(self, dtTime):
        '''
        获取时间对应字符串信息
        :param dtTime:
        :return:
        '''
        nYear = int(dtTime.year)
        nMonth = int(dtTime.month)
        nDay = int(dtTime.day)
        binYear = bin(nYear)
        binMonth = bin(nMonth)
        binDay = bin(nDay)
        # binComb = binYear + binDay.replace('0b', '') + binMonth.replace('0b', '')
        binComb = binYear + binMonth.replace('0b', '') + binDay.replace('0b', '')
        nComb = int(binComb, 2)
        hexComb = hex(nComb)
        return hexComb.replace('0x', '')

    def __GetCurFileDir(self, ):
        # 获取脚本路径
        path = sys.path[0]
        # 判断为脚本文件还是py2exe编译后的文件，如果是脚本文件，则返回的是脚本的目录，如果是py2exe编译后的文件，则返回的是编译后的文件路径
        if os.path.isdir(path):
            return path
        elif os.path.isfile(path):
            return os.path.dirname(path)

    def __GetSecretKeyContent(self):
        filePath = self.__GetCurFileDir() + '/dbRoot.v5'
        if not os.path.exists(filePath):
            return None

        file = open(filePath, "rb")
        if None == file:
            return None

        nLen = os.path.getsize(filePath)
        buffer = file.read(nLen)
        file.close()
        return buffer

    def __SavePic(self, localRootPath, localPicDir, picName, buffer):
        if not os.path.exists(localRootPath):
            return False
        dirPath = localRootPath + '/' + localPicDir
        if not os.path.exists(dirPath):
            os.mkdir(dirPath)
        picPath = dirPath + '/' + picName
        file = open(picPath, "wb")
        if None == file:
            return None
        nLen = len(buffer)
        file.write(buffer)
        file.flush()
        file.close()
        return True

    def __DescryptPic(self, oriPicBuffer, SecretKeyContent):
        try:
            return self.__DescryptPic_Pri(oriPicBuffer, SecretKeyContent)
        except Exception, e:
            print repr(e)
            return None

    def __DescryptPic_Pri(self, oriPicBuffer, SecretKeyContent):
        '''
        解密字符串
        :param oriPicBuffer:
        :param SecretKeyContent:
        :return:
        '''
        nSize = len(oriPicBuffer)
        resBuffer = bytearray(nSize)
        j = 16
        resStrArray = []
        for i in range(0, nSize):
            OriDataChar = oriPicBuffer[i]
            nOriData = ord(OriDataChar)
            SecretKeyDataChar = SecretKeyContent[j + 8]
            nSecretKeyData = ord(SecretKeyDataChar)
            nResDataChar = nOriData^nSecretKeyData;
            resChar = chr(nResDataChar)
            resStrArray.append(resChar)
            j = j + 1
            if(j%8 == 0):
                j = j + 16
            if j >= 1016:
                j = (j + 8)%24
            continue

        retStr = "".join(resStrArray)
        return retStr

#测试代码
# url = 'https://khmdb.google.com/flatfile?db=tm&f1-021023310132121031-i.6-fb102'
# filename = u'C:\\Users\\zhoulei\\Desktop\\周磊test.data'
# WebFileDownload.SimpleDownload(url, filename)


rootUrl = 'https://khmdb.google.com/flatfile?db=tm'
boundRc = [90, 180, 90, 0]
nlevelStart = 6#我查到的是从第4级别开始有效。
nLevelEnd = 7
dtTime = datetime(2005, 12, 31, 0, 0, 0, 0)
localRootDir = '/Users/paiconor/Downloads/GoogleHistoryTiles'
ghtRequest = GoogleHistoryTileMapRequest()
ghtRequest.GetFromRange(rootUrl, boundRc, nlevelStart, nLevelEnd, dtTime, localRootDir)






