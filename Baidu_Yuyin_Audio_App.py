#!/usr/bin/env python3
#encoding=utf-8
import threading
import time
import random
 
import wx
import wx.lib.newevent
 
ItemActivated, EVT_ITEM_ACTIVATED = wx.lib.newevent.NewEvent()


# NOTE: this example requires PyAudio because it uses the Microphone class

import sys  #for exit
import speech_recognition as sr
import struct
import sys
import json
reload(sys)
sys.setdefaultencoding('gbk')

import wave
import urllib, urllib2, pycurl
import base64
import json

################################
from DataUdpSender import DataUdpSender

bufBaiduResults = ''

## get access token by api key &amp; secret key
## 获得token，需要填写你的apikey以及secretkey
def get_token():
    apiKey = "l1i28xGUGlySxbEKk96utOCd"
    secretKey = "609f34eabe98e1d7cce9d46702230387"

    #auth_url = "https://openapi.baidu.com/oauth/2.0/token?grant_type=client_credentials&amp;client_id=" + apiKey + "&amp;client_secret=" + secretKey;
    auth_url = "https://openapi.baidu.com/oauth/2.0/token?grant_type=client_credentials&client_id=" + apiKey + "&client_secret=" + secretKey;
    res = urllib2.urlopen(auth_url)
    json_data = res.read()
    print "json_data", json_data
    return json.loads(json_data)['access_token']

def dump_res(buf):
    #print (buf).encode('gbk')
    global bufBaiduResults
    bufBaiduResults = buf
    print " Buf received from baidu: \n" #, (buf)
    return


## post audio to server
def use_cloud(token, fileName):
    #pathWavefile = r"D:/SpeechRecog/BaiduTest/2016-09-25_22_57_34.wav"
    pathWavefile = fileName
    print u"录音文件名".encode('gbk')
    fp = wave.open(pathWavefile, 'rb')#录音文件名
    ##已经录好音的语音片段
    nf = fp.getnframes()
    f_len = nf * 2
    audio_data = fp.readframes(nf)

    cuid = "8625268" #你的产品id
    srv_url = 'http://vop.baidu.com/server_api' + '?cuid=' + cuid + '&token=' + token
    '''
    http_header = [
        'Content-Type: audio/pcm; rate=8000',
        'Content-Length: %d' % f_len
    ]
    '''
    http_header = [
        'Content-Type: audio/wav; rate=16000',
        'Content-Length: %d' % f_len
    ]

    c = pycurl.Curl()
    c.setopt(pycurl.URL, str(srv_url)) #curl doesn't support unicode
    #c.setopt(c.RETURNTRANSFER, 1)
    c.setopt(c.HTTPHEADER, http_header)   #must be list, not dict
    c.setopt(c.POST, 1)
    c.setopt(c.CONNECTTIMEOUT, 30)
    c.setopt(c.TIMEOUT, 30)
    c.setopt(c.WRITEFUNCTION, dump_res)
    c.setopt(c.POSTFIELDS, audio_data)
    c.setopt(c.POSTFIELDSIZE, f_len)
    strTest = c.perform() #pycurl.perform() has no return val
    print ".... post audio to server is.Done...."


def ParseStringFromBaidu(buffer):
    """
    baidu server returns a JSON string.
    To parse the JSON string to get status and results.
    """
    try:
        inforResults = json.loads(bufBaiduResults, encoding='gbk')
    except ValueError:
        print "ValueError ParseStringFromBaidu"

    if('success.' in inforResults['err_msg']):
        strRecognizedWords = inforResults['result'][0]
        isSuccess = True
    else:
        strRecognizedWords = "Failed this time!"
        isSuccess = False
    return isSuccess, strRecognizedWords


##################################################
class BaiduOnlineRecognitionThread(threading.Thread):

    def __init__(self, mypanel, range_):
        self.mypanel = mypanel
        self.range = range_
        threading.Thread.__init__(self)
        self._token = get_token()  #获得token
        self._isNewAudioRecorded = False
        self._strBaiduResults = ''
        return

    def ClearNewAudioFlag(self):
        self._isNewAudioRecorded = False
        return

    def SetNewAudioFlag(self):
        self._isNewAudioRecorded = True
        return

    def GetToken(self):
        return self._token

    def GetResultsString(self):
        return self._strBaiduResults

    def SetResultsString(self, strResults):
        self._strBaiduResults = strResults
        return

    def run(self):
        #############################################
        token = self.GetToken()

        count = 0
        it = 0
        fileName = "audio_microphone-results.wav"  #TODO:
        print "run baidu cloud"

        while True:
            if self._isNewAudioRecorded:
                print "new audio available to test..."
                timeBegin = time.time()

                ##shibie #进行处理，然后
                use_cloud(token, fileName)

                ###########################################
                ### send results
                inforResults =json.loads(bufBaiduResults)
                if('success.' in inforResults['err_msg']):
                    strRecognizedWords = inforResults['result'][0]
                    strResults = strRecognizedWords
                else:
                    strRecognizedWords = "Failed this time!"
                    strResults = ''
                self.SetResultsString(strResults)

                print "Ready to send in baidu thread:",strRecognizedWords

                timeEnd = time.time()
                strRuntime = " Runtime=%.1fsec"%(timeEnd - timeBegin)

                wx.PostEvent(self.mypanel,
                             ItemActivated(data=1011, #random.randint(*self.range),
                                           thread=threading.current_thread()))
                wx.PostEvent(self.mypanel,
                                #ItemActivated(data ='Results= '.encode('gbk') + strRecognizedWords +'  Sent to:' + MCAST_ADDR + ':' + str(MCAST_PORT) + strRuntime, #random.randint(*self.range), + MCAST_ADDR+ MCAST_PORT
                                ItemActivated(data ='Results= '.encode('gbk') + strRecognizedWords  + strRuntime, #random.randint(*self.range), + MCAST_ADDR+ MCAST_PORT
                                thread=threading.current_thread()))

                self.ClearNewAudioFlag()
        return

#################################################################
class AudioThread(threading.Thread):

    def __init__(self, mypanel, range_):
        self.mypanel = mypanel
        self.range = range_
        self._nCountAudioRecorded = 0
        threading.Thread.__init__(self)
        return

    def GetAudioRecordCount(self):
        return self._nCountAudioRecorded

    def run(self):
        ############  monitoring microphone, and record voice
        count = 0
        it = 0
        r = sr.Recognizer()

        while True:
            with sr.Microphone() as source:
                #print("Say something!")
                audio = r.listen(source)
            #print "recording is done", it

            # write audio to a WAV file
            fileName = "audio_microphone-results.wav"
            with open(fileName, "wb") as f:
                f.write(audio.get_wav_data())
            print  "recording is done", it, "to: ", fileName

            self._nCountAudioRecorded += 1

            wx.PostEvent(self.mypanel,
                         ItemActivated(data=1010, #random.randint(*self.range),
                                       thread=threading.current_thread()))
            count += 1
            it += 1

class WorkerThread(threading.Thread):
 
    def __init__(self, mypanel, range_):
        self.mypanel = mypanel
        self.range = range_
        threading.Thread.__init__(self)
 
    def run(self):
        count = 0
        while count < 15:
            time.sleep(1)
            wx.PostEvent(self.mypanel,
                         ItemActivated(data=random.randint(*self.range),
                                       thread=threading.current_thread()))
            count += 1
 

class MyPanel(wx.Panel):
 
    def __init__(self, parent):

        ########
        saveout = sys.stdout
        fsock = open('out.log', 'w')
        sys.stdout = fsock

        fsockerr = open('error.log', 'w')
        sys.stderr = fsockerr

        #############
        wx.Panel.__init__(self, parent, -1)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
 
        self.mystatic_text = wx.StaticText(self, -1, label="In Main Thread. Waiting for ready......")
        self.sizer.Add(self.mystatic_text)
        self.Bind(EVT_ITEM_ACTIVATED, self.on_item_activated)
 
        self.SetSizerAndFit(self.sizer)

        ################
        commDataUdpSender = DataUdpSender()
        status = commDataUdpSender.InitSocket()
        if(0 == status):
            self.update_text_ui("\n Now, UDP socket ready to use.") # 已UDP连接完成，通讯正常使用。
        else:
            self.update_text_ui("\n Error: UDP Socket error !!! .")
        self._commSocket = commDataUdpSender

        ###################################################################
        #worker_thread1 = WorkerThread(mypanel=self, range_=(1, 100))
        #worker_thread1.daemon = True
        worker_thread2 = AudioThread(mypanel=self, range_=(1000, 2000))
        worker_thread2.daemon = True
        #worker_thread1.start()
        worker_thread2.start()
        self._audioRecordThread = worker_thread2

        baiduThread = BaiduOnlineRecognitionThread(mypanel=self, range_=(1000, 2000))
        baiduThread.daemon = True
        baiduThread.start()
        self._baiduRecognThread = baiduThread
        print "Init is done..."
        return

    def GetCommObject(self):
        return self._commSocket

    def update_text_ui(self, strMsg):
        old_label = self.mystatic_text.GetLabel()
        nNewLines = old_label.count(r'->')
        if(nNewLines > 18):
            old_label = ''
        self.mystatic_text.SetLabel(old_label + strMsg)
        return

    def on_item_activated(self, evt):
        old_label = self.mystatic_text.GetLabel()
        if(evt.data == 1010):
            strEvent = "\n->Event From %s: %s %d" % (evt.thread, 'audio recorded.', self._audioRecordThread.GetAudioRecordCount())

            ## trigger baidu recognition
            self._baiduRecognThread.SetNewAudioFlag()

        elif(evt.data == 1011):
            strEvent = "\n->Event From %s: %s" % (evt.thread, 'Baidu recognization results')

            # send data to receiver.
            strResults = self._baiduRecognThread.GetResultsString()
            if(strResults):
                strResults = strResults.encode(encoding='gbk') + u"..以上是识别结果  ..............................".encode(encoding='gbk')
                buf2Send = struct.pack('<i', 1002)
                msg2Send = bytearray(buf2Send + strResults)
                print "Ready to send in GUI...... "
                status = self.GetCommObject().SendData(msg2Send)
                if(status):
                    strEvent += "\n Error in UDP data sending... "
                else:
                    strEvent += "\n -----> UDP data is sent... "

        elif(evt.data == 1009):
            strEvent = "\n->Event From %s: %s" % (evt.thread, 'Ready to use!')

        else:
            strEvent = "\n->Event From %s: %s" % (evt.thread, evt.data)
        self.update_text_ui(strEvent)
        return
 
##################################################################
if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None, title="wx.PostEvent Example with Threads",
                     size=(850, 400))
    MyPanel(frame)
    frame.CenterOnScreen()
    frame.Show()
    app.MainLoop()