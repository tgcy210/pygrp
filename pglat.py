# -*- coding: utf-8 -*-
"""
Created on Sun Jul 17 15:08:14 2016
pylat.py 


@author: Ce Yi
"""

from __future__ import print_function
from tempfile import mkstemp
from shutil import move
from os import remove, close
# from config import Config
# from subprocess import call
import os.path
import subprocess
import time
import shutil as sh
import numpy as np
# import matplotlib.pyplot as plt

class cfg: 
#----------------------------------------------------------------#
#  configuration class                                           
#  constant vars
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    pgname="lat"
    svlog="lat_solver.log.p0"
#    penmsh = '"e:/workplace/drcc/t04.G04/bin/IVFin3.exe"'
#    titan  = '"e:/workplace/drcc/t04.G04/bin/IVFin5s"'
#    ygroup = '"e:/workplace/drcc/t04.G04/bin/IVFygp.exe"'

    penmsh = '"penmsh.274"'
    ygroup = '"ygroup.147"'
    pdmp   = " >p.tmp"
    ydmp   = " >y.tmp"
# directories
    fwd_dir  = "../mod"     #forward model generate with penmsh
    tfwd_dir = "../tfwd"    #forward transport run with titan
    adj_dir  = "../mod"     #adjoint model generate with penmsh
    tadj_dir = "../tadj"    #adjoint transport run with titan
    xs_dir   = "../xs"      #xs prepare with ygroup 
    resp_dir = "../resp"    #resp calculate with ygroup
# parameters    
    fg_fwd = 1.20604E+00    #reference fine group fwd k-effective
    fg_adj = 1.20635E+00    #reference fine group adj k-effective
    w=np.array([1.0,2.0,2.1])  #PSO bias weights
    
    k_fwd=np.zeros(3,dtype=object)   #outer, keff, kerr  
    k_adj=np.zeros(3,dtype=object)

class cBG:
#----------------------------------------------------------------#
#  Broad group structure class                                           
#  BG related vars
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    nfg=47
    nmax=2
    tfit=0.0005
    twgt=np.array([0.85,0.15],dtype=float)   #fitness resp flux weights
    nout=120  #structure output length in fit##g.out fitness.out, and resp.out
    nmat=2
    mat=[0,1]
    fgfgm=np.loadtxt("../../47g/tfwd/flux.fgm", comments="/")
    fgfgm=fgfgm[mat,:]
    fgagm=np.loadtxt("../../47g/tadj/flux.agm", comments="/")
    fgagm=fgagm[mat,:]
    fgagm=np.multiply(fgagm,fgfgm)
    def  __init__(self, ng, bg):
        self.nbg = ng
        self.bgs= bg
    def  BGstruct(self):    #last group number
        st="1-"
        for i in range(1,self.nbg) :
            st=st+str(self.bgs[i])+" "+str(self.bgs[i]+1)+"-"
        st=st+str(cBG.nfg)
        return st

def replace(file_path, pattern, subst):
#----------------------------------------------------------------#
#  replace pattern with subst in file_path                                          
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    #Create temp file
    fh, abs_path = mkstemp()
    new_file = open(abs_path,'w')
    old_file = open(file_path)
    for line in old_file:
        if pattern in line:
            new_file.write(subst)
        else:
            new_file.write(line)
    #close temp file
    new_file.close()
    close(fh)
    old_file.close()
    #Remove original file
    remove(file_path)
    #Move new file
    move(abs_path, file_path)

def runjob(cmd, arg, wd) :
#----------------------------------------------------------------#
#  run an os command (cmd) in working dir (wd) with arg                                         
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    # run an os command
     my_cmd=cmd+" " +arg 
     print(my_cmd)
     p = subprocess.Popen(my_cmd, shell=True, cwd=wd)
     p.wait()
#     os.waitpid(p.pid, 2)

def qsub_job(scr, tim) :
#----------------------------------------------------------------#
# qsub tfwd and tadj jobs, and check if both jobs are done
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
      
     p = subprocess.Popen("qsub  " + scr  , stdout=subprocess.PIPE, 
                          shell=True, cwd="../tfwd")
     while True :
         line=p.stdout.readline()
         if line   :
             line=line.split('.')
             fwd_id=line[0]
         else :
             break
     print ( fwd_id ) 
     p = subprocess.Popen("qsub " + scr , stdout=subprocess.PIPE, 
                          shell=True, cwd="../tadj")
     while True :
         line=p.stdout.readline()
         if line   :
             line=line.split('.')
             adj_id=line[0]
         else :
             break
     print (adj_id )
     print(" ")
          
     fwd_wait=True
     adj_wait=True
     while True :
         if fwd_wait :
              fwd_wait=False
              p = subprocess.Popen(["qstat", fwd_id], stdout=subprocess.PIPE,
                                   shell=True)
              while True :
                  line=p.stdout.readline()
                  if line   :
                      line=line.split()
                      if fwd_id in line[0] :
                          print (fwd_id+" status(tfwd): " + line[4].strip() )
                          if line[4].strip() != "C" :
                              fwd_wait=True
                  else: 
                      break
                 
         if adj_wait :
              adj_wait=False
              p = subprocess.Popen(["qstat", adj_id], stdout=subprocess.PIPE,
                                   shell=True)
              while True :
                  line=p.stdout.readline()
                  if line   :
                      line=line.split()
                      if adj_id in line[0] :
                          print (adj_id+" status(tadj): " + line[4].strip())
                          if line[4].strip() != "C" :
                              adj_wait=True
                  else: 
                      break
         if fwd_wait or adj_wait :
             time.sleep(tim)
         else: 
             break


def run_case(num_bg, bg_struct, wgt_opt) :
#----------------------------------------------------------------#
#  run a bg_struct with wgt_opt
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    fix_list=""
    my_cmd=""
    my_log=""
    myfile=""
    
#    f = file('autoygp.cfg')
#    cfg = Config(f)

    # bg_struct="1-8 9-30"
    fix_list="fixlst=" + bg_struct + " / pyfixlst \n"
    myfile=cfg.xs_dir + "/ygroup.inp"   #"../xs/ygroup.inp"  
    replace(myfile, "pyfixlst",fix_list) 
    wgt_option="wgtopt="+str(wgt_opt)+ "  /  pywgtopt  \n" 
    replace(myfile, "pywgtopt",wgt_option) 

    my_cmd=cfg.ygroup+"  --log"     # "ygroup.147 --log"
    my_log=cfg.pgname+str(num_bg)+".log" 
    runjob(my_cmd, my_log+cfg.ydmp, cfg.xs_dir)
    
    my_cmd=cfg.xs_dir + "/"+cfg.pgname+"_out.xs" 
    myfile=cfg.tfwd_dir + "/"+cfg.pgname+".xs"
    sh.copyfile(my_cmd, myfile)
    myfile=cfg.tadj_dir + "/"+cfg.pgname+".xs"
    sh.copyfile(my_cmd, myfile)
    
    
    keywds=[
            "Forward Src Spc***",   \
            "Ajoint Src Spc***",    \
            "Reversed***",          \
            "Induced Fission Chi***",  \
            "Sp. Fission Chi***"  ]
    keyflag=0
    myfile="../xs/"+my_log
    fwdsrc=[]
    he3a=[]
    adjsrc=[]
    fschi=[]
    with open(myfile) as f :
        for  line in f :
            for i in range(0,5)  :
                if keywds[i] in line :
                     keyflag=i+1
            if keyflag == 1:
                fwdsrc.append(line)
            elif keyflag == 2 :
                he3a.append(line)
            elif keyflag == 3 :
                adjsrc.append(line)
            elif keyflag == 4 :
                fschi.append(line)
            elif keyflag == 5 :
                break
    
    f.close()
    
    
    # copy he3a.1toG file
#    myfile=cfg.xs_dir+"/he3a.1toG"
#    f=open(myfile,"w")
#    for item in he3a[2:] :
#        f.write("%s" % item)
#    f.close()
    
    #run penmshxp in fwd folder
    myfile=cfg.fwd_dir+"/lat.chi"
    f=open(myfile,"w")
    for item in fschi[2:] :
        f.write("%s" % item)
    f.close()
    
    str_ngrp="2,1,1,1," +str(num_bg) + ",14,2  / pyngrp f \n"
    myfile=cfg.fwd_dir+"/penmsh.inp"    
    replace(myfile, "pyngrp",str_ngrp) 
    ihm=num_bg+3
    str_ihm="1, 2, 3, "+ str(ihm) + "   /pyihm f \n"
    replace(myfile, "pyihm",str_ihm) 
    
    my_cmd=cfg.penmsh 
    runjob(my_cmd, cfg.pdmp , cfg.fwd_dir )
    my_cmd=cfg.fwd_dir + "/lat_titan.inp" 
    myfile=cfg.tfwd_dir+"/lat.tan"
    sh.copyfile(my_cmd, myfile)
#    runjob(my_cmd, myfile, cfg.fwd_dir )
    
    #run penmshxp in adj folder
    myfile=cfg.adj_dir+ "/lat.chi"
    f=open(myfile,"w")
    for item in fschi[2:] :
        f.write("%s" % item)
    f.close()
    
    str_ngrp="2,1,1,1," +str(num_bg) + ",14, 1  / pyngrp a \n"
    myfile=cfg.adj_dir+"/penmsh.inp"    
    replace(myfile, "pyngrp",str_ngrp) 
    ihm=num_bg+3
    str_ihm="1, 2, 3, "+ str(ihm) + "   /pyihm a \n"
    replace(myfile, "pyihm",str_ihm) 
    
    my_cmd=cfg.penmsh 
    runjob(my_cmd,cfg.pdmp, cfg.adj_dir )
    my_cmd=cfg.adj_dir + "/lat_titan.inp"
    myfile=cfg.tadj_dir+"/lat.tan"
    sh.copyfile(my_cmd, myfile)
    
#   submit jobs
    qsub_job("n1lat.scr", 30)

#forward run
#    my_cmd=cfg.titan    
#    runjob(my_cmd, " -n lat.tan -flx", cfg.tfwd_dir)
#adjoint run
#    runjob(my_cmd, " -n lat.tan -flx -adj ", cfg.tadj_dir)
#    time.sleep(1)
    
    my_cmd=cfg.penmsh
    runjob(my_cmd, " -i ../mod -f -ff -fgm "+cfg.pdmp, cfg.tfwd_dir)
    runjob(my_cmd, " -i ../mod -f -fa -agm "+cfg.pdmp, cfg.tadj_dir)
    
#    str_numgrp="numgrp=" + str(num_bg) + "  /pynumgrp \n "
#    myfile=cfg.resp_dir + "/ygroup.inp"
#    replace(myfile, "pynumgrp",str_numgrp) 
#    str_xsn=("xsnihm=" + str(num_bg*2+2) + " xsniht=3 xsnihs=" +  
#            str(3+num_bg) + "  /pyxsn \n" )
#    replace(myfile, "pyxsn",str_xsn) 
#    
#    my_cmd=cfg.ygroup
#    runjob(my_cmd, cfg.ydmp, cfg.resp_dir)
    

    myfile=cfg.tfwd_dir + "/"+cfg.svlog
    with open(myfile) as f:
        for line in f:
            if "Outer=" in line:
                cfg.k_fwd=line.split()[1:7:2]  #outer keff kerr
    cfg.k_fwd[0]=int(cfg.k_fwd[0])               
    cfg.k_fwd[1]=float(cfg.k_fwd[1]) 
    cfg.k_fwd[2]=float(cfg.k_fwd[2]) 
    
    myfile=cfg.tadj_dir + "/"+cfg.svlog
    with open(myfile) as f:
        for line in f:
            if "Outer=" in line:
                cfg.k_adj=line.split()[1:7:2]  #outer keff kerr
    cfg.k_adj[0]=int(cfg.k_adj[0])               
    cfg.k_adj[1]=float(cfg.k_adj[1]) 
    cfg.k_adj[2]=float(cfg.k_adj[2])                

    
    f=open("keff.out","a")
    # f.write("# BG    BG structure                                         forward          adjoint \n")
    f.write("{0:4d}    {1:{nst}s}  {2:40s}  {3:40s} \n".format(num_bg,
            bg_struct,str(cfg.k_fwd),str(cfg.k_adj),nst=cBG.nout) )
    f.close()
#    return k_fwd[1], k_adj[1]

def get_mat() :
#----------------------------------------------------------------#
# get material list
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    name=np.genfromtxt("../mod/lat.mba", comments="/",
                       dtype=None,usecols=(0,))
    return name

def run_2g() :    
#----------------------------------------------------------------#
#  run a 2-g case 
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    wgt=1
    for g in range (1,30) :
        bg_struct="1-"+str(g)+" "+str(g+1)+"-30"
        print ("Case: " + bg_struct)
        run_case(2, bg_struct,wgt)


def run_bg(num_bg) :    
#----------------------------------------------------------------#
#  run a set of cases with #ofBG=num_bg 
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    runstr="Case Suite :num_bg="+str(num_bg)
    f=open("resp.out","a")
    f.write("*****   ***************            **********       ******* \n")
    f.write(runstr+" \n")
#    f.write("# BG    BG structure               forward          adjoint \n")
    f.write("{0:4s}    {1:50s}  {2:15s}  {3:15s} \n".format("# BG", "BG structure","forward","adjoint") )
    f.close()
    
    f=open("ferr.out","a")
    f.write("*****   ***************            **********       ******* \n")
    f.write(runstr+" \n")
    f.close()
    wgt=4

    

    #Mat3:Poly 4:Al 7:He3 8:water 9:air

    mat=[0, 1]
    mat_name=get_mat()
    mat_name=mat_name[mat]
    fgfgm=np.loadtxt("../../47g/tfwd/flux.fgm", comments="/")
    fgfgm=fgfgm[mat,:]

    fgagm=np.loadtxt("../../47g/tadj/flux.agm", comments="/")
    fgagm=fgagm[mat,:]
    fgagm=np.multiply(fgagm,fgfgm)
    # print (fgagm)
    for g in range (8 ,9) :
    #    bg_struct="1-3 4-7 8-10 11-14 15-17 18-20 21-24 25-"+str(g)+" "+str(g+1)+"-30"
    #    bg_struct="1-"+str(g)+" "+str(g+1)+"-25" + " 26-30"
    #    bg_struct="1-"+str(g)+" "+str(g+1)+"-30"   #2-g
    #    bg_struct="1-7 8-"+str(g)+" "+str(g+1)+"-30"   #3-g
    #    bg_struct="1-7 8-"+str(g)+" "+str(g+1)+"-25 26-30"   #4-g
        bg_struct="1-3 4-7 8-"+str(g)+" "+str(g+1)+"-20 21-25 26-30"   #5-g
    #    st=np.array([0,3,7,10,14,17,20,24,g,30])     #last fine group for each broad group, start from 0
        st=np.array([0,3,7,g,20,25,30])     #last fine group for each broad group, start from 0
        print ("Case: " + bg_struct)
        cgfgm=np.zeros((5,num_bg))
        cgagm=np.zeros((5,num_bg))
        for i  in range(5) :
            for j in range(num_bg) :
                cgfgm[i,j]=np.sum(fgfgm[i,st[j]:(st[j+1])])
                cgagm[i,j]=np.sum(fgagm[i,st[j]:(st[j+1])])
        cgagm=np.divide(cgagm,cgfgm)

        run_case(num_bg, bg_struct,wgt)
        
        # print (cgagm)
        fgm=np.loadtxt("../tfwd/flux.fgm",comments="/")
        agm=np.loadtxt("../tadj/flux.agm", comments="/")
        
        fgm=fgm[mat,:]
        agm=agm[mat,:]
        f=open("../resp/ygroup.log")
        for line in f :
            if "Forward Response" in line :
                line=line.split()
                resp_fwd=line[-1]
            elif "Adjoint Response" in line :
                line=line.split()
                resp_adj=line[-1]
        f.close()
        fval=GetFitness()
        print (fval)
        f=open("ferr.out","a")
        f.write("----------------------------------------------------------\n")
        f.write("Flux err output for Case: " + bg_struct + "  \n")
        f.write("Fwd Resp: " + resp_fwd + "\n")
        f.write("Adj Resp: " + resp_adj + "\n")
        #f.write("FG Collapsed fwd flux -------  \n")
        #np.savetxt(f,cgfgm,fmt="%12.5e")
        #f.write("FG Collapsed adj flux -------  \n")
        #np.savetxt(f,cgagm,fmt="%12.5e")
        #f.write("BG Simulated fwd flux -------  \n")
        #np.savetxt(f,fgm, fmt="%12.5e")
        #f.write("BG Simulated adj flux -------  \n")
        #np.savetxt(f,agm,fmt="%12.5e")
        fgm=np.divide(fgm-cgfgm,cgfgm)
        agm=np.divide(agm-cgagm,cgagm) 
        absfgm=np.absolute(fgm)
        absagm=np.absolute(agm)
        f.write("Fwd-flux rel.err (min max mean) {0:8.4f}  {1:8.4f}  {2: 8.4f} \n".format(np.amin(absfgm),np.amax(absfgm),np.mean(absfgm)))
        f.write("Adj-flux rel.err (min max mean) {0:8.4f}  {1:8.4f}  {2: 8.4f} \n".format(np.amin(absagm),np.amax(absagm),np.mean(absagm)))
        f.write("BG-Simulated to FG-Collapsed fwd flux rel.error (mat\BG) \n")
        np.savetxt(f,fgm,fmt="%8.3f")
        f.write("BG-Simulated to FG-Collapsed adj flux rel.error (mat\BG) \n")
        np.savetxt(f,agm,fmt="%8.3f")
        f.close()

def GetFitness(num_bg,st) :
#----------------------------------------------------------------#
#  Calculate fitness for a group structure
#  st: structure array  
#  e.g. "1-3 4-8 9-20 21-30" -> [0,3, 8,20,30] (bg_st -> st)
#  return fitness metrics (ferr, ffgm , fagm)  
#
#  ferr= | fitness  unused    unused    |    --overall fitness
#        | RMSresp  Fwd.resp  Adj.resp  |    --resp.rel.err
#        | RMSflux  Fwd.flux  Adj.flux  |    --fluxr.rel.err
#
#  ffgm or fagm= | m_0  BG_1  BG_2 .... BG_H |    --fwd/adj rel.flx.err for Material 1 
#                | m_1  BG_1  BG_2 .... BG_H |    --fwd/adj rel.flx.err for Material 2
#                | ...  ...   ...  ...  BG_H | 
#                | m_M  ...   ...  ...  BG_H |    --fwd/adj rel.flx.err for material M-1
# Where:
# M: #ofMat-1 ; H: #ofBG  ; RMS=root mean square
# m_i=RMS(BG_i, i=1,H) for i'th row
# RMSresp=RMS(Fwd.resp Adj.resp) 
# RMSflux=RMS(Fwd,flux Adj.flux)  Fwd/adj.flux=RMS(m_i, i=0,M) 
# fitness=w0*RMSresp+w1*RMSflux, where w0,w1 are constant weights 
#
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#

    
#    myfile=cfg.tfwd_dir + "/"+cfg.svlog
#    with open(myfile) as f:
#        for line in f:
#            if "Outer=" in line:
#                keff_fwd=float(line.split()[3])
#    
#    myfile=cfg.tadj_dir + "/"+cfg.svlog
#    with open(myfile) as f:
#        for line in f:
#            if "Outer=" in line:
#                keff_adj=float(line.split()[3])
    keff_fwd=float(cfg.k_fwd[1])
    keff_adj=float(cfg.k_adj[1])            
    ferr=np.zeros(shape=(3,3),dtype=float)
    var_fwd=(keff_fwd-cfg.fg_fwd)/cfg.fg_fwd
    var_adj=(keff_adj-cfg.fg_adj)/cfg.fg_adj
    fit=(var_fwd**2+var_adj**2)/2
    fit=fit**0.5
    ferr[1,:]=[fit,var_fwd,var_adj]
    
    fname=cfg.tfwd_dir+"/flux.fgm"
    fgm=np.loadtxt(fname,comments="/")
    fname=cfg.tadj_dir+"/flux.agm"    
    agm=np.loadtxt(fname, comments="/")
        
    fgm=fgm[cBG.mat,:]
    agm=agm[cBG.mat,:]
    cgfgm=np.zeros(shape=(cBG.nmat,num_bg),dtype=float)
    cgagm=np.zeros(shape=(cBG.nmat,num_bg),dtype=float)
    for i  in range(cBG.nmat) :
        for j in range(num_bg) :
            cgfgm[i,j]=np.sum(cBG.fgfgm[i,st[j]:(st[j+1])])
            cgagm[i,j]=np.sum(cBG.fgagm[i,st[j]:(st[j+1])])
    cgagm=np.divide(cgagm,cgfgm)
    fgm=np.divide(fgm-cgfgm,cgfgm)
    agm=np.divide(agm-cgagm,cgagm) 
    absfgm=np.absolute(fgm)
    absagm=np.absolute(agm)
    ffgm=np.zeros(shape=(cBG.nmat,num_bg+1),dtype=float)    
    fagm=np.zeros(shape=(cBG.nmat,num_bg+1),dtype=float)
    ffgm[:,1:]=absfgm
    fagm[:,1:]=absagm
    for i in range(cBG.nmat):
        rms=np.sqrt(np.mean(np.square(absfgm[i,:])))
        ffgm[i,0]=rms
        rms=np.sqrt(np.mean(np.square(absagm[i,:])))
        fagm[i,0]=rms
    var_fwd=np.sqrt(np.mean(np.square(ffgm[:,0])))
    var_adj=np.sqrt(np.mean(np.square(fagm[:,0])))
    fit=(var_fwd**2+var_adj**2)/2.0
    fit=fit**0.5
    ferr[2,:]=[fit,var_fwd,var_adj]   
    ferr[0,0]=cBG.twgt[0]*ferr[1,0]+cBG.twgt[1]*ferr[2,0]
    return ferr,ffgm, fagm


def GetFitness2()  :
#----------------------------------------------------------------#
#  test fitness 
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    fval=np.random.random()
    fval=fval**2
    return fval,fval*2,fval*3


def autoygp(n_bg,n_pa) :   # nb: # of BG; np: # of Particles
#----------------------------------------------------------------#
#  Particle Swarm Optimization 
#  n_bg=#ofBG  n_pa=#ofParticles
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#

    pt=np.random.dirichlet([1]*n_bg, n_pa)
    pt=pt*cBG.nfg
    pt=pt.round()
    
    pt=pt.astype(int)   
    pt[pt==0]=1
    ps=pt.sum(axis=1)

    for j in range(0,n_pa) :
        n_diff=ps[j]-cBG.nfg        
         
        if n_diff > 0 :
            for i in range(n_diff) :
                i_arg=np.argmax(pt[j,:])

                pt[j,i_arg]=pt[j,i_arg]-1
        elif n_diff < 0 :
            for i in range(-n_diff) :
                i_arg=np.argmin(pt[j,:])
                pt[j,i_arg]=pt[j,i_arg]+1
    s_t=np.zeros(shape=(n_pa,n_bg+1),dtype=int) 
  
    s_sum=np.zeros(n_pa,dtype=int)
    
    for i in range(n_bg) :
        s_sum[:]=s_sum[:] + pt[:,i]        
        s_t[:,i+1]=s_sum[:]
    
    p_str=np.zeros(shape=(n_pa,n_bg+1),dtype=int) 
    p_str=s_t.copy()                          #particle best structure
    g_str=np.zeros(n_bg+1,dtype=int)
    np.copyto(g_str,s_t[0,:])    
    
    p_fit=np.zeros(n_pa,dtype=float)  # particle best fitness
    p_fit[:]=1.0
    g_fit=1.0
    p_spd=np.zeros(shape=(n_pa,n_bg+1),dtype=float)
    spd=np.zeros(n_pa, dtype=int)    
    n=0
    fit=1.0
    wgt_opt=4
    
    strfit=GetFit(n_bg)
    runfit={}
    newfit={}   
    while ( n < cBG.nmax and (g_fit>cBG.tfit)) :
        n=n+1
        for j in range(n_pa)  :
            abg=cBG(n_bg,s_t[j,:])
            bg_st=abg.BGstruct()
            if strfit.has_key(bg_st) :
                fit=strfit[bg_st][0]
                runfit[bg_st]=strfit[bg_st]
            else:
                print("Run Case : " + bg_st)
                run_case(n_bg, bg_st, wgt_opt) 
                afit,rfwd,radj=GetFitness(n_bg,s_t[j,:])
                strfit[bg_st]=[afit[0,0],afit[1,0],afit[2,0]] #[fit,rfwd,radj]
                runfit[bg_st]=strfit[bg_st] #afit[0,:] #[fit,rfwd,radj]
                newfit[bg_st]=strfit[bg_st] #afit[0,:] #[fit,rfwd,radj]
                fit=afit[0,0]
                if fit < g_fit:
                    g_fit=fit
                    np.copyto(g_str[:],s_t[j,:])
                    OutOne(afit,rfwd,radj,n_bg,bg_st)
                    f=open("keff.out","a")
                    f.write("{0:4s}: {1:{nst}s}  fit= {2:s}  \n".format("ghit",str(g_str), str(g_fit),nst=cBG.nout ) )
                    f.close()   
            if fit < p_fit[j] :
                p_fit[j]=fit
                np.copyto(p_str[j,:],s_t[j,:])
            if fit < g_fit:
                g_fit=fit
                np.copyto(g_str[:],s_t[j,:])
        
        for j in range (n_pa) :
            for i in range (1,n_bg) :
                r1=np.random.random()
                r2=np.random.random()
                p_dif=p_str[j,i]-s_t[j,i]
                g_dif=g_str[i]-s_t[j,i]
                p_spd[j,i]=cfg.w[0]*p_spd[j,i]+cfg.w[1]*r1*p_dif
                p_spd[j,i]=p_spd[j,i]+cfg.w[2]*r2*g_dif
                spd[j]=s_t[j,i]+int(p_spd[j,i])
                if spd[j] <= s_t[j,i-1] :
                    spd[j]=s_t[j,i-1]+1
                if spd[j] > cBG.nfg-n_bg+i :
                    spd[j]=cBG.nfg-n_bg+i
                s_t[j,i]=spd[j]
        f=open("keff.out","a")
        f.write("n={0:<4d} st={1:{nst}s} gfit=  {2:15s}  \n".format(n,str(g_str), str(g_fit),nst=cBG.nout-3 ) )
        f.close()
    
    f=open("fitness.out","a")
#    f.write("{0:{nst}s}   {1:25s}  \n".format("#BG structure", "Fitness    Resp.RMS   Flux.RMS",nst=cBG.nout ) )
    for s in runfit: 
        f.write("{0:{nst}s}   {1:10f} {2:10f} {3:10f} \n".format(s,strfit[s][0],strfit[s][1],strfit[s][2],nst=cBG.nout ) )
    f.close()
    OutFit(n_bg, newfit)

# run batch header in resp.out
def file_header(num_bg) :    
#----------------------------------------------------------------#
#  outfile resp.out header
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    import time
    timstr=time.strftime('%X %x %Z')  # 16:08:12 05/08/03 AEST 
#    time.strftime('%l:%M%p %Z on %b %d, %Y')
    
    runstr="Case Suite :num_bg="+str(num_bg) + "   " + timstr 
    f=open("keff.out","a")
    f.write("*****   ***************            **********       ******* \n")
    f.write(runstr+" \n")
#    f.write("# BG    BG structure               forward          adjoint \n")
    f.write("{0:4s}    {1:{nst}s}  {2:40s}  {3:40s} \n".format("# BG", \
             "BG structure","forward","adjoint",nst=cBG.nout ) )
    f.close()
    
    f=open("fitness.out","a")
    f.write("*****   ***************            **********       ******* \n")
    f.write(runstr+" \n")
    f.write("{0:{nst}s} {1:25s}  \n".format("#BG structure", \
            "    Fitness    Resp.RMS   Flux.RMS",nst=cBG.nout ) )
    f.close()

    runstr="Case run: num_bg="+str(num_bg) + "   " + timstr 
    f=open("tryone.out","a")
    f.write("*****   ***************            **********       ******* \n")
    f.write(runstr+" \n")
    f.close()

def GetFit(num_bg):
#----------------------------------------------------------------#
#  Load fitness results from previous generated dictionary
#  in file fit##g.out   where ## is #ofBG
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    fname="fit"+str(num_bg).zfill(2) + "g.out"
    fitdict={}    
    key=np.zeros(num_bg+1,dtype=int)
    val=np.zeros(3,dtype=float)
    if os.path.isfile(fname) :
        f=open(fname,"r")
        for line in f:
            sline=line.strip()
            if not sline.startswith("#"):
                curline=line.replace("-",".")
                curdata=[float(s) for s in curline.split()]
                for i in range(1,num_bg) :
                    key[i]=int(curdata[i])-1
                key[num_bg]=cBG.nfg
                for i in range(3):
                    val[i]=curdata[i+num_bg]
                abg=cBG(num_bg,key)                
                skey=abg.BGstruct()                  
                fitdict[skey]=val
    return fitdict

def OutFit(num_bg, fit):
#----------------------------------------------------------------#
#  save newly generaged dictionary items into file        
#  in file fit##g.out   where ## is #ofBG
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    fname="fit"+str(num_bg).zfill(2) + "g.out"
    f=open(fname,"a")
    f.write("{0:{nst}s}   {1:25s}  \n".format("#BG structure", "Fitness    Resp.RMS   Flux.RMS",nst=cBG.nout ) )
    for s in fit: 
         f.write("{0:{nst}s}   {1:10f} {2:10f} {3:10f} \n".format(s, fit[s][0],fit[s][1],fit[s][2],nst=cBG.nout) )
    f.close()
    
def TryOne(num_bg, bg_st):
#----------------------------------------------------------------#
#  Run one case with full outputs                         
#  in file tryone.out                    
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    run_case(num_bg,bg_st,4)
    s_t=Convert2St(bg_st,num_bg)
    afit,rfwd,radj=GetFitness(num_bg,s_t)
    OutOne(afit,rfwd,radj,num_bg,bg_st) 

def OutOne(afit,rfwd,radj,num_bg,bg_st) : 
#----------------------------------------------------------------#
#  output full metrics for a group structure Run one                         
#  in file tryone.out                    
#  Author:  Ce Yi 
#  
#----------------------------------------------------------------#
    f=open("tryone.out","a")
    f.write("*********one-case run*********** \n")
    f.write("BG struct: {0:42s} \n".format(bg_st))
    f.write("Fitness:    {0:12.6f} \n".format(afit[0,0]))
    f.write("Resp.Rel.Err(RMS fwd adj) : {0:s} \n".format("   ".join([str('%12.6f' % item) for item in afit[1,:]]) ))
    f.write("Flux.Rel.Err(RMS fwd adj) : {0:s} \n".format("   ".join([str('%12.6f' % item) for item in afit[2,:]]) ))

    f.write("Fwd.Flx.Rel.Err: Mat.Name:(RMS bg_num)       \n")
    f.write("{0:16s}{1:10s}{2:s} \n".format("Mat.Name","RMS",(" "*5).join("BG_"+str('%02d' % item) for item in range (1,num_bg+1)) ) )
  
    mat_name=get_mat()
    mat_name=mat_name[cBG.mat]
    for i in range(cBG.nmat) :
        f.write("{0:16s}{1:s} \n".format(mat_name[i],"  ".join(['{0:<8.3%}'.format(item) for item in rfwd[i,:]]) ))
    f.write("Adj.Flx.Rel.Err: Mat.Name:(RMS bg_num)       \n")
    f.write("{0:16s}{1:10s}{2:s} \n".format("Mat.Name","RMS",(" "*5).join("BG_"+str('%02d' % item) for item in range (1,num_bg+1)) ) )

    for i in range(cBG.nmat) :
        f.write("{0:16s}{1:s} \n".format(mat_name[i],"  ".join(['{0:<8.3%}'.format(item) for item in radj[i,:]]) ))
    f.write(" \n")
    f.close()
    
def Convert2St(bg_st,num_bg):
#----------------------------------------------------------------#
#  Convert bg_st to st                                    
#  Author:  Ce Yi 
#  e.g. "1-3 4-8 9-20 21-30" -> [0,3, 8,20,30] (bg_st -> st)
#  
#----------------------------------------------------------------#
    curline=bg_st.replace("-",".")
    curdata=[float(s) for s in curline.split()]
    st=np.zeros(num_bg+1,dtype=int)
    for i in range(1,num_bg) :
        st[i]=int(curdata[i])-1
    st[num_bg]=cBG.nfg
    return st
    
def GetFlow() : 
#----------------------------------------------------------------#
#  Read in fine flow pressure data                           
#  in cfg.xs_dir/flow.dat                    
#  Author:  Ce Yi 
#  created 09/04/2015
#
#----------------------------------------------------------------#
    myfile=cfg.xs_dir + "/flow.dat"
    keystr={"Down-stream Flow Pressure":"dsfp",    
             "Up-stream Flow Pressure":"usfp" ,
             "Down-Stream Flow":"dsf",
             "Up-Stream Flow":"usf",
             "In-group Flow (Broad Group 1+2)":"igft",
             "In-group Flow :Broad Group  1":"igf1",
             "In-group Flow :Broad Group  2":"igf2",
             "Total Flow":"tf",
             "Net Flow Pressure":"nfp"}
    block=[]
    flowdata={}

    with open(myfile) as f:
        for line in f:
            #read in a key-block
            for key in keystr:
                
                if key in line :
                    numline=cBG.nfg if "Pressure" in key else cBG.nfg-1
                    for _ in range(1):  #skip one line
                        next(f)
                    for num, line in enumerate(f,1):
                                                
                        if num <= numline:
                            block.append(line)
                        else:
                            break
                    pds=np.loadtxt(block,usecols=(m+1 for m in cBG.mat))
                    flowdata[keystr[key]]=pds.transpose()
                    block=[]
    
    return flowdata  
#***************************************************
#  autoygp run 
num_bg=3
num_pa=4 
flow=GetFlow()
file_header(num_bg)
autoygp(num_bg,num_pa)

#***************************************************
# Run one-case
#bg_st="1-1 2-8 9-11 12-17 18-30"
#bg_st="1-1 2-7 8-11 12-17 18-30"
#bg_st="1-7 8-9 10-11 12-13 14-16 17-27 28-30" 
# bg_st="1-7 8-8 9-10 11-11 12-16 17-17 18-30"       
#bg_st="1-7 8-12 13-22 23-30"
#bg_st="1-7 8-17 18-22 23-30"
#bg_st="1-4 5-6 7-7 8-8 9-9 10-10 11-11 12-23 24-24 25-25 26-26 27-27 28-28 29-29 30-30"
# bg_st="1-1 2-2 3-3 4-4 5-5 6-6 7-7 8-8 9-9 10-10 11-11 12-12 13-20 21-24 25-30"
# TryOne(num_bg,bg_st)

#***************************************************
# run OneOut
#num_bg=11
#bg_st="1-6 7-8 9-11 12-12 13-15 16-18 19-21 22-27 28-28 29-29 30-30"
#bg_st="1-4 5-6 7-10 11-11 12-16 17-17 18-18 19-23 24-26 27-29 30-30"
#s_t=Convert2St(bg_st,num_bg)
#afit,rfwd,radj=GetFitness(num_bg,s_t)
#OutOne(afit,rfwd,radj,num_bg,bg_st)  

#***************************************************
# mat_name=get_mat()
#f = file('autoygp.cfg')
#cfg = Config(f)
#my_fil=cfg.xs_dir + "/ygroup.inp"    
#fix_list="1-30"
#replace(my_fil, "pyfixlst",fix_list) 
#print (my_fil)

#runjob(cfg.penmsh," ",cfg.fwd_dir)
#runjob(cfg.titan, "-n drcc.tan ", cfg.tfwd_dir)
#runjob(cfg.penmsh," ",cfg.adj_dir)

