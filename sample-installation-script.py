#!/usr/bin/python
import socket
import sys, getopt
import urllib2, re
import urllib, os
import shutil, subprocess
def main(argv):
   buildnumber = ''
   version = ''
   hostfile=''
   domain=''
   try:
      opts, args = getopt.getopt(argv,"b:v:p:d",["buildnumber=","version=","hostfile=","domain="])
   except getopt.GetoptError:
      print 'esxinstaller.py -b <buildnumber> -v <version> -p <hostfile>'
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print 'test.py -b <buildnumber> -v <version> -p<hostfile>'
         sys.exit()
      elif opt in ("-b", "--buildnumber"):
        buildnumber = arg
      elif opt in ("-v", "--version"):
         version = arg
      elif opt in ("-p", "--hostfile"):
         hostfile = arg 
      elif opt in ("-d", "--domain"):
         domain = sys.argv[-1:]
         
   print 'Buildnumber is ', buildnumber
   print 'version is ', version
   print 'hostfile is ', hostfile
   print 'domain is', domain[0]
   validatemastercfg(hostfile,version)
   prepare_mac_file(hostfile)
   downloadbuild(buildnumber,version)
   modify_boot_cfg(os.path.join(os.getcwd(),"esxi-"+buildnumber))
   resetesxi(os.getcwd(),buildnumber,hostfile) 
   cmdforsuite() 
   powercycle()
    
def downloadbuild(buildnumber,version):
   url="http://build-squid.eng.vmware.com/build/mts/release/bora-"+buildnumber+"/publish/"+version+"/"
   response = urllib2.urlopen(url)
   urlcontent= response.read() 
   m=re.search('VMware-VMvisor-Installer.*.iso', urlcontent)
   print m.group(0)
   match=m.group(0).split(">")
   vmwarecomponent=match[0][:-1]
   newurl=url+vmwarecomponent
   print newurl
   print "Downloading esx build "+vmwarecomponent
   isobuild = urllib.URLopener()
   isobuild.retrieve(newurl,vmwarecomponent)
   umountiso("/mnt/loop/")
   removefile("/tmp/"+vmwarecomponent) 
   path=os.path.join(os.getcwd(),"esxi-"+buildnumber)
   if not os.path.exists(path):
         makedir(path)
   else:
       print "The directory "+path+ " already exists"

   # Moving file to another folder to perform loop mount.
   filepath=os.getcwd()+"/"+vmwarecomponent
   movefile(filepath,"/tmp")
   mountiso("/tmp/"+vmwarecomponent,"/mnt/loop")
   copycontent("/mnt/loop/*",path)
  

def makedir(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            print Path+ " was already there"

def movefile(source, destination):
     try:
        shutil.move(source,destination) 
     except OSError:
        print destination +" was already there"

def usage():
   print "Please correct the parameters to the script"

def mountiso(source,destination):
  print "Peforming loop mount from "+source+" on "+destination
  cmd="mount -o loop,ro %s %s " %(source,destination)
  p=subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,)
  out,err = p.communicate('print err') 
  print out 

def copycontent(source,destination):
    print "Copying the contents of the file from"+ source +" to "+ destination
    cmd = "cp -fr %s %s" %(source,destination)
    os.system(cmd)

def removefile(path):
   if os.path.isfile(path):
        os.remove(path)
   elif os.path.isdir(path):
        os.remove(path)
   elif os.path.islink(path):
        os.remove(path) 

def umountiso(destination):
    print "unmounting all mount points"
    cmd="umount %s >  /dev/null 2>&1" %(destination)
    os.system(destination)

def searchbigmac(mac):
     bigmac=os.getcwd()+"/"+"MAC"
     print bigmac
     bf=open(bigmac,'r')
     for line in bf:
        if re.search(mac, line):
          m= re.search(mac, line)
          return line
     bf.close()

def prepare_mac_file(hostfile):
    print "prepare small mac file" 
    f=open(os.getcwd()+"/"+hostfile,'r+')
    allhosts=f.readlines()
    print allhosts
    f.close()
    nf=open(os.getcwd()+"/"+hostfile,'w')
    for host in allhosts:
        nhost=host.split("\n")[0]
        print nhost
        newline=searchbigmac(nhost)
        nf.write(str(newline))
    nf.close()

def search_boot_cfg(searchitem,bootcfg):
     bf=open(bootcfg,'r')
     for line in bf:
          if re.search(searchitem, line):
               bf.close()
               return line      
     bf.close()


def modify_boot_cfg(path):
    os.mknod("temp.cfg")
    print path
    bootcfg=os.path.join(path,"boot.cfg")
    bootcfgorig=os.path.join(path,"boot.cfg.orig")
    print bootcfg
    print bootcfgorig
    print "Taking a backup of the original boot.cfg"
    copycontent(bootcfg,bootcfgorig)
    bootstate=search_boot_cfg("bootstate",bootcfg)
    #Open Tmp.cfg for writing
    print bootstate 
    f=open("temp.cfg",'w')
    f.write(bootstate)
    title=search_boot_cfg("title", bootcfg)
    f.write(title)
    print title
    kernel=search_boot_cfg("kernel=", bootcfg)
    kernelorig="/tboot.b00"
    kernelnew="http://%s/esxi-default/tboot.b00" %(ipaddress())
    f.write("%s//%s/%s"%(kernel,kernelorig,kernelnew))    
    kernelopt=search_boot_cfg("kernelopt=",bootcfg)
    kerneloptorig="runweasel"
    kerneloptnew="ks=http://%s/masterks.cfg"%(ipaddress())
    f.write("%s//%s/%s"%(kernelopt,kerneloptorig,kerneloptnew))
    f.write(get_modules(bootcfg))
    f.write("build=")
    f.write("updated=0")
    f.close()
    movefile("temp.cfg", bootcfg) 
    


def get_modules(filename):
     cmd="cat %s | grep  modules | tr -d '/'"%(filename)
     p=subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,)
     out,err = p.communicate('through in to out')
     return out 


def ipaddress():
    return str(socket.gethostbyname(socket.getfqdn()))    
    

def symlink(source, destination):
    cmd="ln -s %s %s"%(source, destination)
    p=subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,)
    out,err = p.communicate('through in to out')
    print out 
   
def resetesxi(path,buildnumber,hostfile):
    removefile("/var/www/html/esxi-default")
    mac="mac"
    newpath=os.path.join(path,"esxi-%s"%buildnumber)
    symlink(newpath,"/var/www/html/esxi-default")
    umountiso("/mnt/loop")
    removefile("/tmp/*")
    removefile("/path%s"%(mac))
    symlink("/path%s"%(hostfile),"/path%s"%(mac))
     
def validatemastercfg(hostfile,version):
   masterkcfg="masterks%s-%s.cfg"%(version.split("-")[1][0],hostfile)
   if os.path.isfile(masterkcfg) and os.access(masterkcfg, os.R_OK):
     print "File exists and is readable"
   else:
     print "Either %s is missing or is not readable"%(mastercfg)
     sys.exit(2)
     

def cmdforsuite():
    macfile=os.path.join(os.getcwd(),"mac")
    f=open(macfile,'r')
    for line in f:
      host,macaddr=line.split(",")
      print host
      print macaddr 
      cmd1="/home/pxeuser/PXEconfig.pl -l WDC -d mts/home5 -f amishra/pxe/pxelinux.cfg/default.gpxe -m %s"%(macaddr)
      print cmd1
      cmd2="/home/pxeuser/PXEconfig.pl -g -l WDC -d mts/home5 -f amishra/pxe/viewst-gpxe-m %s"%(macaddr)
      print cmd2
      remotexecution(cmd1)
      remotexecution(cmd2)
    f.close()
      
def powercycle():
    macfile=os.path.join(os.getcwd(),"mac")
    f=open(macfile,'r')
    for line in f:
       host,macaddr=line.split(",")
       powercmd="/opt/dell/srvadmin/bin/racadm5 -r %s  -u <hidden> -p <hidden> serveraction powercycle &"%(host)
       print powercmd 
       remotexecution(powercmd)
    f.close()  

def remotexecution(cmd):
    print os.environ['SSH_ASKPASS']
    user="pxeuser"
    SERVER="suite.eng.vmware.com"
    SSH_OPTIONS="-oLogLevel=error  -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null "
    print "Executing command on the suite server %s" %(cmd)
    cmd="setsid ssh %s %s@%s %s"%(SSH_OPTIONS,user,SERVER,cmd)
    os.system(cmd)
    
   
if __name__ == "__main__":
  main(sys.argv[1:])
