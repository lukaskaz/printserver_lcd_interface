import LCD_1in44
import LCD_Config

import RPi.GPIO as GPIO
from PIL import Image,ImageDraw,ImageFont,ImageColor
from time import sleep
from os import system
import unicodedata
import threading
import subprocess
from enum import Enum
import sys
import os
import unidecode
import logging

this_module = sys.modules[__name__]
logger = logging.getLogger(__name__)  
logging.basicConfig(level = logging.DEBUG, \
format='[%(levelname)s][%(asctime)s][%(process)d] %(message)s')

KEY_UP_PIN     = 6 
KEY_DOWN_PIN   = 19
KEY_LEFT_PIN   = 5
KEY_RIGHT_PIN  = 26
KEY_PRESS_PIN  = 13
KEY1_PIN       = 21
KEY2_PIN       = 20
KEY3_PIN       = 16

#init GPIO
GPIO.setmode(GPIO.BCM) 
#GPIO.cleanup()
GPIO.setup(KEY_UP_PIN,      GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Input with pull-up
GPIO.setup(KEY_DOWN_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(KEY_LEFT_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(KEY_RIGHT_PIN,   GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
GPIO.setup(KEY_PRESS_PIN,   GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
GPIO.setup(KEY1_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
GPIO.setup(KEY2_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
GPIO.setup(KEY3_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up

HWKEYBUTTONS = [ KEY_UP_PIN, KEY_DOWN_PIN, KEY_LEFT_PIN, KEY_RIGHT_PIN, KEY_PRESS_PIN, KEY1_PIN, KEY2_PIN, KEY3_PIN ]

def userselectedkey(channel):
    global keyselection
    if channel == KEY_UP_PIN:
        keyselection = key.up
    elif channel == KEY_DOWN_PIN:
        keyselection = key.down
    elif channel == KEY_LEFT_PIN:
        keyselection = key.left
    elif channel == KEY_RIGHT_PIN:
        keyselection = key.right
    elif channel == KEY_PRESS_PIN:
        keyselection = key.confirm
    elif channel == KEY1_PIN:
        keyselection = key.func1
    elif channel == KEY2_PIN:
        keyselection = key.func2
    elif channel == KEY3_PIN:
        keyselection = key.func3


class key(Enum):
    none    = 0
    up      = 1
    down    = 2
    left    = 3
    right   = 4
    confirm = 5
    func1   = 6
    func2   = 7
    func3   = 8

class menus(Enum):
    def __lt__(self, elem):
        return self.value < elem.value
    def __int__(self):
        return self.value
    cpu      = 0
    mem      = 1
    uptime   = 2
    ipaddr   = 3
    temp     = 4
    time     = 5
    history  = 6
    mainonly = 7
    details  = 8
    main     = 9

menuitems = { menus.cpu:['show cpu load', 'displaycpuloadmenu', 0, False], menus.mem:['show memory state', 'displaymemorymenu', 0, False], menus.uptime:['show os uptime', 'displayuptimemenu', 0, False], menus.ipaddr:['show ip address', 'displayipmenu', 0, False], menus.temp:['show cpu temp', 'displaycputempmenu', 0, False], menus.time:['show current time', 'displaytimemenu', 0, False], menus.history:['show print history', 'displayprinthistory', 7, True], menus.details:['show print details', 'displayprintdetails', 1, False] ,menus.main:['show main menu', 'displaymainmenu', 7, True] }

menutextcolor         = (0,    96,   0) #dark green
submenutextcolor      = (128,   0,   0) #dark red
nowprinttextcolor     = (255,   0,   0) #norm red
printmenutextcolor    = (0,     0, 128) #dark blue
printmenuerrtextcolor = (0,     0, 255) #dark blue
highlightcolor        = (192, 192, 192) #norm grey
jobtoshow = 0
killthreads = False

invalidstatus = 'invalid'
printslastdonejob = 0
printslist = []
keyselection = key.none
suspendssaver = False

def normalizediacritics(string, use=False):
    if use == True:
        string = str(string)
        string = unidecode.unidecode(string).encode('ascii')
        return string.decode('utf-8')
    return string

def splitstringtolcd(string, font = None):
    if font == None:
        font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 11)

    stringlen = font.getsize(string)[0]
    if stringlen > 128:
        tmpstr = ""
        lastchar = 0
        for idx, ch in enumerate(string):
            tmpstr += ch
            if font.getsize(tmpstr)[0] > 128:
                lastchar = idx - 1
                break
        stringfirst = string[:lastchar] + '~'
        stringsecond = '~' + string[lastchar:]
        return True,stringfirst,stringsecond
    else:
        return False,string,''

def getprintjobs():
    outputprints = []
    processprints = subprocess.Popen(['lpstat', '-W', 'completed', '-o'], stdout=subprocess.PIPE, encoding='iso-8859-2')
    if processprints.wait() == 0:
        outputprints = processprints.communicate()[0].strip().split('\n')
    return len(outputprints), outputprints

def extractjobdetails(job, chkpending = False):
    if chkpending: idxsta = -2; idxfil = -1
    else: idxsta = 1; idxfil = 2
    jobstatus = invalidstatus
    if len(job) > 3:
        job = list(filter(None, job))
        jobprinter = job[0][:job[0].find(' ')]
        jobstatus = normalizediacritics(job[idxsta][job[idxsta].find(':')+1:job[idxsta].find('[')].replace(' ', ''))
        jobowner = normalizediacritics(job[idxsta][:job[idxsta].find(':')-1])
        jobnum = job[idxsta][job[idxsta].find('[')+1:job[idxsta].find(']')-1].split(' ')
        if len(jobnum) == 3: jobnum = jobnum[1]
        job = ' '.join(job[idxfil].split()).split(' ')
        jobsize = ' '.join(job[-2:])
        jobfile = ''
        if job[0].find('smbprn') == 0:
            jobfile = normalizediacritics(' '.join(job[1:-2]))
        #[job, jobnum, jobprinter, jobowner, jobfile, jobsize, jobdate]
        return jobstatus,[jobnum, jobprinter, jobowner, jobfile, jobsize]
    return jobstatus,[]

def getprintjobdetails(job):
    jobnum = job[0].rfind('-')
    jobnum = job[0][jobnum+1:]
    jobowner = job[1]
    jobdate = normalizediacritics(job[3] + " " + job[4] + " " + job[5] + " " + job[6] + " " + job[7])
    jobdate = jobdate.replace(',', '')
    processjob = subprocess.Popen(['lpq', '-l', jobnum], stdout=subprocess.PIPE, encoding='iso-8859-2')
    if processjob.wait() == 0:
        outputjob = processjob.communicate()[0].strip().split('\n')
        outputjob[-1] = outputjob[-1].encode('latin2', errors='ignore').decode('utf-8', errors='ignore')
        jobstatus,jobdetails = extractjobdetails(outputjob)
        if jobstatus != invalidstatus: 
            jobdetails.insert(0, job)
            jobdate = jobdate.encode('latin2', errors='ignore').decode('utf-8', errors='ignore')
            jobdetails.append(jobdate)
            #[job, jobnum, jobprinter, jobowner, jobfile, jobsize, jobdate]
            #logging.debug('getprintjobdetails: ' + str(jobstatus) + ", " + str(jobdetails))
        return jobstatus,jobdetails
    return jobstatus,[]

def getprintlastdonejob():
    processjobfiles = subprocess.Popen(['ls', '-1t', '/var/spool/cups'], stdout=subprocess.PIPE, encoding='utf-8')
    if processjobfiles.wait() == 0:
        outputjobfiles = processjobfiles.communicate()[0]
        outputjobfiles = outputjobfiles.strip().split('\n')
        for elem in outputjobfiles:
            if elem[0] == 'c':
                lastjob = elem
                break
        return int(lastjob[1:])
    return 0

def updateprinthistory():
    global printslist
    global printslastdonejob
    global killthreads

    while killthreads == False:
        currprintlastjob = getprintlastdonejob()
        if currprintlastjob != printslastdonejob:
            printslastdonejob = currprintlastjob
            del printslist[:]
            logging.info("Updating print history...")
            outputprintslen, outputprints = getprintjobs()
            if outputprintslen:
                for job in outputprints:
                    job = " ".join(job.split()).split(' ')
                    if len(job) == 8:
                        jobstatus,jobdetails = getprintjobdetails(job)
                        if jobstatus == invalidstatus:
                            continue
                        printslist.append(jobdetails)
                        printslist.sort(key = lambda x: int(x[1]), reverse = True)
                        sleep(0.1)
                logging.info("Print history update completed!")
            subprocess.run(["systemctl", "restart", "cups"], stderr=subprocess.DEVNULL)
        else:
            sleep(5)
    logging.debug("Killing thread: " + str(updateprinthistory.func_name))

def displayonejobdetails(LCD, selection):
    global jobtoshow
    textcolor = printmenutextcolor
    backcolor = highlightcolor
    linesel = selection[0]
    keysel = selection[1]
    jobnum = selection[2]
        
    image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 11)

    linepos = 2
    for num in range(jobtoshow, jobtoshow + 4):
        if (num + 1) == (jobtoshow + jobnum):
            if num >= len(printslist): break
            reqjob = printslist[num][0][0]
            reqowner = printslist[num][3]
            reqfile = printslist[num][4]
            reqdate = printslist[num][6]
            issplit,reqjobfirst,reqjobsecond = splitstringtolcd(reqjob)
            if issplit == True:
                draw.text((2, linepos), reqjobfirst, font = font, fill = textcolor)
                linepos = linepos + 12
                draw.text((2, linepos), reqjobsecond, font = font, fill = textcolor)
                linepos = linepos + 16
            else:
                draw.text((2, linepos), reqjob, font = font, fill = textcolor)
                linepos = linepos + 16

            issplit,reqfilefirst,reqfilesecond = splitstringtolcd(reqfile)
            if issplit == True:
                draw.text((2, linepos), reqfilefirst, font = font, fill = textcolor)
                linepos = linepos + 12
                draw.text((2, linepos), reqfilesecond, font = font, fill = textcolor)
                linepos = linepos + 16
            else:
                draw.text((2, linepos), reqfile, font = font, fill = textcolor)
                linepos = linepos + 16

            draw.text((2, linepos), reqowner, font = font, fill = textcolor)
            linepos = linepos + 16
            draw.text((2, linepos), reqdate, font = font, fill = textcolor)

            if keysel == key.down:
                draw.rectangle([(28, 128-14), (98, 126)], fill = backcolor)
                draw.text((30, 128-14), "> REPRINT <", font = font, fill = textcolor)
                LCD.LCD_ShowImage(image, 0, 0)
                displayprinthistoryjob(LCD, num)
            else:
                draw.text((30, 128-14), "> REPRINT <", font = font, fill = textcolor)
                LCD.LCD_ShowImage(image, 0, 0)
            break

def displayprinthistoryjob(LCD, num):
    if waitjoykeypress() == True:
        if num >= len(printslist): return
        #[job, jobnum, jobprinter, jobowner, jobfile, jobsize, jobdate]
        reqjobnum = printslist[num][1]
        reqjobfile = printslist[num][4]
        printcommand = "lp -i {} -H restart".format(reqjobnum)
        ret = system(printcommand)
        if ret:
                textcolor = printmenuerrtextcolor
                image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
                draw = ImageDraw.Draw(image)
                font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)
                fontinfo = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBoldOblique.ttf', 11)

                linepos = 42
                draw.text((20, linepos), "CANNOT PRINT", font = font, fill = textcolor)
                info = reqjobnum + ":" + reqjobfile
                linepos = linepos + 16
                issplit,infofirst,infosecond = splitstringtolcd(info, fontinfo)
                if issplit == True:
                    draw.text((2, linepos), infofirst, font = fontinfo, fill = textcolor)
                    linepos = linepos + 12
                    draw.text((2, linepos), infosecond, font = fontinfo, fill = textcolor)
                    linepos = linepos + 16
                else:
                    draw.text((2, linepos), info, font = fontinfo, fill = textcolor)
                    linepos = linepos + 16

                LCD.LCD_ShowImage(image, 0, 0)
                sleep(5)

def displayprintdetails(LCD, selection):
    textcolor = nowprinttextcolor
    backcolor = highlightcolor
    linesel = selection[0]
    keysel = selection[1]
    jobnum = selection[2]

    if keysel == key.confirm:
        return menus.history
    else:
        displayonejobdetails(LCD, selection)

    return menus.details


def displayprinthistory(LCD, selection):
    global jobtoshow
    textcolor = printmenutextcolor
    backcolor = highlightcolor
    linesel = selection[0]
    keysel = selection[1]

    image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 11)

    if keysel == key.confirm and linesel > 0:
        if linesel < 5:
            return menus.details
        elif linesel == 5: jobtoshow = jobtoshow + 4 if jobtoshow < len(printslist) else len(printslist)
        elif linesel == 6: jobtoshow = jobtoshow - 4 if jobtoshow > 0 else 0
        else: return menus.main 
    else:
        if keysel == key.left: jobtoshow = jobtoshow - 4 if jobtoshow > 0 else 0
        elif keysel == key.right: jobtoshow = jobtoshow + 4 if jobtoshow < len(printslist) else len(printslist)

        #[job, jobnum, jobprinter, jobowner, jobfile, jobsize, jobdate]
        linepos = 2
        for num in range(jobtoshow, jobtoshow + 4):
            if num < len(printslist):
                if (num + 1) == (jobtoshow + linesel):
                    draw.rectangle([(1, linepos), (126, linepos+12)], fill = backcolor)
                if printslist[num][1] and printslist[num][4]:
                    reqname = str(printslist[num][1]) + ":" + str(printslist[num][4])
            elif num == len(printslist):
                reqname = "==== END OF LIST ===="
            else: break

            issplit,reqnamefirst,reqnamesecond = splitstringtolcd(reqname)
            if issplit == True:
                draw.text((2, linepos), reqnamefirst, font = font, fill = textcolor)
                linepos = linepos + 12
                draw.text((2, linepos), reqnamesecond, font = font, fill = textcolor)
                linepos = linepos + 16
            else:
                draw.text((2, linepos), reqname, font = font, fill = textcolor)
                linepos = linepos + 16
        if linesel == 5:
            draw.rectangle([(1, 128-14), (44, 126)], fill = backcolor)
        elif linesel == 6:
            draw.rectangle([(44, 128-14), (87, 126)], fill = backcolor)
        elif linesel == 7:
            draw.rectangle([(87, 128-14), (127, 126)], fill = backcolor)
        draw.text((2, 128-14), ">NEXT", font = font, fill = textcolor)
        draw.text((45, 128-14), ">PREV", font = font, fill = textcolor)
        draw.text((88, 128-14), ">MAIN", font = font, fill = textcolor)

    LCD.LCD_ShowImage(image, 0, 0)
    return menus.history

def showongoingprints(LCD):
    global jobtoshow
    global killthreads

    textcolor = nowprinttextcolor
    while killthreads == False:
        outputprints = []
        processjob = subprocess.Popen(['lpq', '-l'], stdout=subprocess.PIPE, encoding='iso-8859-2')
        if processjob.wait() == 0:
            outputjob = processjob.communicate()[0].strip().split('\n')
            outputjob[-1] = outputjob[-1].encode('latin2', errors='ignore').decode('utf-8', errors='ignore')
            jobstatus,jobdetails = extractjobdetails(outputjob, chkpending = True)
            if jobstatus == 'active':
                showlcdscreenimage(LCD, setsuspend = True, issuspended = True)
                image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
                draw = ImageDraw.Draw(image)
                font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)
                fontinfo = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBoldOblique.ttf', 11)
                printjobnum = jobdetails[0]
                printfile = jobdetails[3]
                printowner = jobdetails[2]

                info = printjobnum + ":" + printfile + ", from: " + printowner
                linepos = 42
                draw.text((20, linepos), "PRINTING NOW", font = font, fill = textcolor)
                linepos = linepos + 16
                issplit,infofirst,infosecond = splitstringtolcd(info, fontinfo)
                if issplit == True:
                    draw.text((2, linepos), infofirst, font = fontinfo, fill = textcolor)
                    linepos = linepos + 12
                    draw.text((2, linepos), infosecond, font = fontinfo, fill = textcolor)
                    linepos = linepos + 16
                else:
                    draw.text((2, linepos), info, font = fontinfo, fill = textcolor)
                    linepos = linepos + 16

                LCD.LCD_ShowImage(image, 0, 0)
                while True:
                    processjob = subprocess.Popen(['lpq', '-l'], stdout=subprocess.PIPE, encoding='iso-8859-2')
                    if processjob.wait() == 0:
                        outputjob = processjob.communicate()[0].strip().split('\n')
                        jobstatus,_ = extractjobdetails(outputjob, chkpending = True)
                        if jobstatus != 'active': break
                        else: sleep(1)
                showlcdscreenimage(LCD, setsuspend = True, issuspended = False)
                #[job, jobnum, jobprinter, jobowner, jobfile, jobsize, jobdate]
                #logging.debug('showongoingprints: ' + str(jobstatus) + ", " + str(jobdetails))
        sleep(0.25)
    logging.debug("Killing thread: " + str(showongoingprints.func_name))

def displaymainmenu(LCD, selection):
    textcolor = menutextcolor
    backcolor = highlightcolor
    linesel = selection[0]
    keysel = selection[1]

    if keysel != key.confirm:
        if linesel == 0:
            image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)

            linepos = 2
            draw.text((2, linepos), "> MAIN MENU <", font = font, fill = textcolor)

            linepos = 20
            for num,(item,submenu) in enumerate(menuitems.items()):
                if item < menus.mainonly:
                    menuname = submenu[0]
                    draw.text((2, linepos), menuname, font = font, fill = textcolor)
                    linepos = linepos + 14
            LCD.LCD_ShowImage(image, 0, 0)
        elif linesel > 0:
            image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)

            linepos = 2
            draw.text((2, linepos), "> MAIN MENU <", font = font, fill = textcolor)

            linepos = 20
            image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)

            linepos = 2
            draw.text((2, linepos), "> MAIN MENU <", font = font, fill = textcolor)

            linepos = 20
            for num,(item,submenu) in enumerate(menuitems.items()):
                if item < menus.mainonly:
                    menuname = submenu[0]
                    if (num + 1) == linesel:
                        draw.rectangle([(1, linepos), (126, linepos+12)], fill = backcolor)
                    if menuname != None:
                        draw.text((2, linepos), menuname, font = font, fill = textcolor)
                    linepos = linepos + 14
            LCD.LCD_ShowImage(image, 0, 0)
    elif linesel > 0:
        return menus(linesel-1)
    return menus.main

def displayipmenu(LCD, selection):
    textcolor = submenutextcolor
    linesel = selection[0]
    keysel = selection[1]

    if keysel != key.confirm:
        image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)

        processip = subprocess.Popen(['ip', '-4', 'a','sh', 'wlan0'], stdout=subprocess.PIPE)
        outputip = str(processip.communicate()[0])
        ipaddrstart = outputip.find("inet")
        ipaddrend = outputip.find("brd")
        dnsstart = ipaddrstart
        dnsend = outputip.find("/24")
        ipaddr = outputip[ipaddrstart:ipaddrend].split()
        dnsname = outputip[dnsstart:dnsend].split()
        processdns = subprocess.Popen(['nslookup', '192.168.1.112'], stdout=subprocess.PIPE)
        outputdns = str(processdns.communicate()[0])
        dnsstart = outputdns.find("name = ")
        dnsname = outputdns[dnsstart:].split()
        ipaddr = "IP: " + ipaddr[1][:-3]
        dnsname = "DNS: " + dnsname[2][:-1]

        linepos = 2
        draw.text((2, linepos), "> IPv4 ADDRESS <", font = font, fill = textcolor)
        linepos = linepos + 16
        draw.text((2, linepos), ipaddr, font = font, fill = textcolor)
        linepos = linepos + 12
        draw.text((2, linepos), dnsname, font = font, fill = textcolor)

        LCD.LCD_ShowImage(image, 0, 0)
    else:
        return menus.main
    return menus.ipaddr

def displaycpuloadmenu(LCD, selection):
    textcolor = submenutextcolor
    keysel = selection[1]

    if keysel != key.confirm:
        image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)

        processcpuload = subprocess.Popen(['mpstat'], stdout=subprocess.PIPE, encoding='utf-8')
        outputcpuload = processcpuload.communicate()[0]
        outputcpuload = outputcpuload.strip().split('\n')[-1]
        addr = " ".join(outputcpuload.split(' ')).replace(",", ".").split()
        cpuload = float(addr[2]) + float(addr[4])
        cpuload = "Total load -> {:.1f}".format(cpuload) + ' %'
        linepos = 2
        draw.text((2, linepos), "> CPU UTILIZATION <", font = font, fill = textcolor)
        linepos = linepos + 16
        draw.text((2, linepos), cpuload, font = font, fill = textcolor)

        LCD.LCD_ShowImage(image, 0, 0)
        return menus.cpu
    return menus.main

def displaycputempmenu(LCD, selection):
    textcolor = submenutextcolor
    keysel = selection[1]

    if keysel != key.confirm:
        image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)

        processtemp = subprocess.Popen(['cat', '/sys/class/thermal/thermal_zone0/temp'], stdout=subprocess.PIPE, encoding='utf-8')
        outputtemp = processtemp.communicate()[0].strip()
        outputtemp = "{:.1f}".format(float(outputtemp)/1000)
        outputtemp = "Core temp -> " + str(outputtemp) + ' \xb0C'
        linepos = 2
        draw.text((2, linepos), "> CPU TEMP <", font = font, fill = textcolor)
        linepos = linepos + 16
        draw.text((2, linepos), outputtemp, font = font, fill = textcolor)

        LCD.LCD_ShowImage(image, 0, 0)
        return menus.temp
    return menus.main

def displaymemorymenu(LCD, selection):
    textcolor = submenutextcolor
    keysel = selection[1]

    if keysel != key.confirm:
        image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)

        processmem = subprocess.Popen(['free', '-h', '-t'], stdout=subprocess.PIPE, encoding='utf-8')
        outputmem = processmem.communicate()[0]
        outputmem = outputmem.strip().split('\n')
        mem = " ".join(outputmem[1].split(' ')).split()
        swap = " ".join(outputmem[2].split(' ')).split()
        total = " ".join(outputmem[3].split(' ')).split()
        linepos = 2
        draw.text((2, linepos), "> MEM UTILIZATION <", font = font, fill = textcolor)
        linepos = linepos + 16
        line = mem[0][:-1] + " [sum][used][free]" 
        draw.text((2, linepos), line, font = font, fill = textcolor)
        linepos = linepos + 12
        line = "[" + str(mem[1]) + "] [" + str(mem[2]) + "] [" + str(mem[3]) + "]"
        draw.text((2, linepos), line, font = font, fill = textcolor)
        linepos = linepos + 16
        line = swap[0][:-1] + " [sum][used][free]" 
        draw.text((2, linepos), line, font = font, fill = textcolor)
        linepos = linepos + 12
        line = "[" + str(swap[1]) + "] [" + str(swap[2]) + "] [" + str(swap[3]) + "]"
        draw.text((2, linepos), line, font = font, fill = textcolor)
        linepos = linepos + 16
        line = total[0][:-1] + " [sum][used][free]" 
        draw.text((2, linepos), line, font = font, fill = textcolor)
        linepos = linepos + 12
        line = "[" + str(total[1]) + "] [" + str(total[2]) + "] [" + str(total[3]) + "]"
        draw.text((2, linepos), line, font = font, fill = textcolor)

        LCD.LCD_ShowImage(image, 0, 0)
        return menus.mem
    return menus.main

def displayuptimemenu(LCD, selection):
    textcolor = submenutextcolor
    keysel = selection[1]

    if keysel != key.confirm:
        image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)

        processuptime = subprocess.Popen(['uptime', '-p'], stdout=subprocess.PIPE, encoding='utf-8')
        outputuptime = processuptime.communicate()[0]
        outputuptime = outputuptime.strip().split(', ')
        linepos = 2
        draw.text((2, linepos), "> OS UPTIME <", font = font, fill = textcolor)
        linepos = linepos + 16
        for part in outputuptime:
            draw.text((2, linepos), part, font = font, fill = textcolor)
            linepos = linepos + 12

        LCD.LCD_ShowImage(image, 0, 0)
        return menus.uptime
    return menus.main

def displaytimemenu(LCD, selection):
    textcolor = submenutextcolor
    keysel = selection[1]

    if keysel != key.confirm:
        image = Image.new("RGB", (LCD.width, LCD.height), "WHITE")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 11)

        processdate = subprocess.Popen(['date', "+%a, %d %b %Y"], stdout=subprocess.PIPE, encoding='utf-8')
        processtime = subprocess.Popen(['date', "+%T"], stdout=subprocess.PIPE, encoding='utf-8')
        outputdate = processdate.communicate()[0].strip()
        outputtime = processtime.communicate()[0].strip()
        linepos = 2
        draw.text((2, linepos), "> OS DATE/TIME <", font = font, fill = textcolor)
        linepos = linepos + 16
        draw.text((2, linepos), normalizediacritics(outputdate), font = font, fill = textcolor)
        linepos = linepos + 12
        draw.text((2, linepos), outputtime, font = font, fill = textcolor)

        LCD.LCD_ShowImage(image, 0, 0)
        return menus.time
    return menus.main


def waitjoykeypress(retries = -1):
    while retries:
        if iskeypressed(key.confirm):
            return True
        elif iskeypressed(key.up) or iskeypressed(key.down) or \
iskeypressed(key.left) or iskeypressed(key.right):
            break
        else:
            if retries > 0:
                retries -= 1
            sleep(0.1)
    return False

def iskeypressed(key):
    global keyselection
    resp = (keyselection == key)
    if resp == True:
        keyselection = key.none
    return resp

def showlcdscreenimage(LCD, setsuspend = False, issuspended = False):
    global suspendssaver

    if setsuspend:
        suspendssaver = issuspended

    if suspendssaver == False:
        image = Image.open('printer.bmp')
        LCD.LCD_ShowImage(image, 0, 0)

def callmenufunction(LCD, menulvl, selection, callfunc = True):
    global suspendssaver

    submenu = menuitems[menulvl]
    menufunc = getattr(this_module, submenu[1])
    menuelems = submenu[2]
    menussaver = submenu[3]
    if callfunc == True and suspendssaver == False:
        menulvl = menufunc(LCD, selection)
    return menulvl, menuelems, menussaver

def displaymenu(LCD):
    global jobtoshow
    global keyselection

    line = 0
    jobnum = 0
    menulvl = menus.main
    prevmenulvl = menulvl
    selection = [line, key.none, jobnum]

    ssaverdelay = 50
    showlcdscreenimage(LCD)
    menulvl,menuelems,menussaver = callmenufunction(LCD, menulvl, selection, callfunc = False)
    while True:
        if iskeypressed(key.up):
            line = line - 1 if line > 1 else 1
            selection = [ line, key.up, jobnum ] 
        elif iskeypressed(key.down):
            line = line + 1 if line < menuelems else menuelems
            selection = [ line, key.down, jobnum ] 
        elif iskeypressed(key.right):
            selection = [ line, key.right, jobnum ] 
        elif iskeypressed(key.left):
            selection = [ line, key.left, jobnum ]
        elif iskeypressed(key.func1):
            selection = [ 0, key.func1, jobnum ]
            if menulvl == menus.main: menulvl = menulvl.history
            elif menulvl == menus.history: menulvl = menulvl.main
        elif iskeypressed(key.func2):
            selection = [ 0, key.func2, jobnum ]
            if menulvl == menus.main: menulvl = menulvl.mem
        elif iskeypressed(key.func3):
            selection = [ 0, key.func3, jobnum ]
            if menulvl == menus.main: menulvl = menulvl.time
        elif iskeypressed(key.confirm):
            selection = [ line, key.confirm, jobnum ] 
        elif menussaver == True:
            if ssaverdelay > 0:
                ssaverdelay -= 1
                if not ssaverdelay:
                    line = 0
                    menulvl = prevmenulvl = menus.main
                    selection = [ line, key.none, jobnum ]
                    showlcdscreenimage(LCD)
                elif line > 0:
                    if menulvl == menus.history:
                        if(prevmenulvl == menus.main or selection[1] == key.func1):
                            line = 1
                            jobtoshow = 0
                            selection = [ line, key.none, jobnum ]
                            ssaverdelay = 100
                    elif menulvl == menus.main:
                        if(prevmenulvl == menus.history or selection[1] == key.func1):
                            line = int(menus.history) + 1
                            selection = [ line, key.none, jobnum ]

                    prevmenulvl = menulvl
                    menulvl,menuelems,menussaver = callmenufunction(LCD, menulvl, selection)
                    if (menulvl == menus.details): jobnum = line
                    selection = [ line, key.none, jobnum ]
                else:
                    sleep(0.1)
            continue
        else:
            menulvl,menuelems,menussaver = callmenufunction(LCD, menulvl, selection)
            if menulvl == menus.history:
                line = jobnum
                ssaverdelay = 100
            selection = [ line, key.none, jobnum ] 
            sleep(0.1)
            continue
        ssaverdelay = 50

def main():
    LCD = LCD_1in44.LCD()
    Lcd_ScanDir = LCD_1in44.SCAN_DIR_DFT  #SCAN_DIR_DFT = D2U_L2R
    LCD.LCD_Init(Lcd_ScanDir)
    #LCD.LCD_Clear()

    for key in HWKEYBUTTONS:
        GPIO.add_event_detect(key, GPIO.FALLING, callback=userselectedkey, bouncetime=250)

    threading.Thread(target=updateprinthistory, args=()).start()
    threading.Thread(target=showongoingprints, args=(LCD, )).start()
    displaymenu(LCD)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        try:
            killthreads = True
            logging.info("\nInterrupted by keyboard!")
            sys.exit(0)
        except SystemExit:
            os._exit(0)	

