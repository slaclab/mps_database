import subprocess
import os

class Latex:
    file_name = 'latex.tex'

    def __init__(self,file_name):
        self.file_name = file_name
        self.f = open(file_name,'w')

    def getAuthor(self):
        proc = subprocess.Popen('whoami', stdout=subprocess.PIPE)
        user = proc.stdout.readline().rstrip().decode('UTF-8')
        email = ""
        name = ""
        first_name = "unknown"
        last_name = "unknown"
        proc = subprocess.Popen(['person', '-tag', '-match', 'email', user], stdout=subprocess.PIPE)
        while True:
          line = proc.stdout.readline().decode('UTF-8')
          if line != '':
            if line.startswith("email") and email == "":
              email = line.split(':')[1].rstrip().lower()
            elif line.startswith("name") and name == "":
              name = line.split(':')[1].rstrip()
              first_name = name.split(', ')[1]
              last_name = name.split(', ')[0]
          else:
            break
        return [user, email, first_name, last_name]

    def exportPdf(self, report_path):
        fname = self.file_name.rsplit('/',1)[-1]
        cwd = os.getcwd()
        os.chdir(report_path)
        os.environ["TEXINPUTS"] = '.:../../../templates/latex/:../../../templates/latex/fmtcount:'
        cmd = 'pdflatex {0}'.format(fname)
        os.system(cmd)
        os.system(cmd)
        os.system(cmd)
        nfname = fname.replace('tex','pdf')
        cmd = 'mv {0} ../'.format(nfname)
        os.system(cmd)
        os.chdir(cwd)        

    def startDocument(self, title, version):
        self.f.write('\\documentclass[10pt, oneside]{book}\n')
        self.f.write('\\usepackage{lcls-article}\n')
        self.f.write('\\usepackage{longtable}\n')
        self.f.write('\\usepackage{tabularx}\n')
        self.f.write('\\newcommand\code{\\begingroup \\urlstyle{tt}\\Url}\n')
        self.f.write('\\renewcommand\\revnum{0}{1}{2}'.format('{',version,'}\n'))
        self.f.write('\\title{0}{1}{2}{3}{4}'.format('{',title,':\\\\',version,'}\n'))
        self.f.write('\\date{}\n')
        self.f.write('\\begin{document}\n')
        self.f.write('\\maketitle\n')
        self.f.write('\\addtocounter{page}{1}\n')

    def endDocument(self, report_path):
        self.f.write('\\end{document}\n')
        self.f.close()
        self.exportPdf(report_path)

    def crateProfile(self,lc1_id, shm, rack, slots):
        self.f.write('\\begin{table}[H]\n')
        self.f.write('\\centering\n')
        self.f.write('\\makegapedcells\n')
        self.f.write('\\begin{tabularx}{\\textwidth}{|c c c Y<{\\rule[0em]{0pt}{1.1em}}|}\n')
        self.f.write('{0}{1}{2}\n'.format('\\multicolumn{4}{l}{',rack,'}\\\\'))
        self.f.write('{0}{1}{2}\n'.format('\\multicolumn{4}{l}{',shm,'}\\\\'))
        self.f.write('\\hline\n')
        self.f.write('Slot & App ID & Type & Description\\\\\n')
        self.f.write('\\hline\n')
        for slot in slots:
          self.f.write('{0} & {1} & {2} & {3} \\\\\n'.format(slot[0],slot[1],slot[2],slot[3]))
          self.f.write('\\hline\n')
        self.f.write('\\end{tabularx}\n')
        self.f.write('\\end{table}\n')

    def writeAppInputs(self, slot, inputs):
        self.f.write('\\subsubsection{Device Inputs}\n')
        self.f.write('\\begin{longtable}{@{}ccclll@{}}\n')
        self.f.write('\\toprule\n')
        self.f.write('\\multicolumn{1}{@{}c}{LN} & \\multicolumn{1}{c}{CN}  & \\multicolumn{1}{c}{Channel} & \\multicolumn{1}{c}{Device Name} & \\multicolumn{1}{c@{}}{Input Name} & \\multicolumn{1}{c@{}}{Device Type} \\\\\n')
        self.f.write('\\midrule\n')
        self.f.write('\\endfirsthead\n')
        self.f.write('\\multicolumn{5}{c}{\\ldots continued from previous page} \\\\\n')
        self.f.write('\\midrule\n')
        self.f.write('\\multicolumn{1}{@{}c}{LN} & \\multicolumn{1}{c}{CN} & \\multicolumn{1}{c}{Channel} & \\multicolumn{1}{c}{Device Name} & \\multicolumn{1}{c@{}}{Input Name} & \\multicolumn{1}{c@{}}{Device Type} \\\\\n')
        self.f.write('\\midrule\n')
        self.f.write('\\endhead\n')
        self.f.write('\\midrule\n')
        self.f.write('\\multicolumn{5}{c}{continued on next page\\ldots} \\\\\n')
        self.f.write('\\endfoot\n')
        self.f.write('\\bottomrule\n')
        self.f.write('\\endlastfoot\n')
        for input in inputs:
          self.f.write('{0} & {1} & {2}{3}{4}{5}{6}{7}{8}{9}'.format('$\\Box$','$\\Box$',input[0],' & \\texttt{',input[1].replace('_','\_'),'} & \\texttt{',input[2].replace('_','\_'),'} & \\texttt{',input[3].replace('_','\_'),'}\\\\\n'))
        self.f.write('\\end{longtable}\n')

    def writeDigitalLogicTable(self,state,logic,inputs,title):
        self.f.write('{0}{1}{2}'.format('\\subsection{',title.replace('_',' '),'}\n'))
        self.f.write('\\begin{center}\n')
        if len(inputs) == 2:
          self.f.write('\\begin{tabular}{@{}lcccccc@{}}\n')
          self.f.write('\\toprule\n')
          self.f.write('Name & $B$ & $A$ & LINAC & DIAG0 & HXU & SXU \\\\\n')
          self.f.write('\\midrule\n')
          self.f.write('{0} & {1} & {2} & {3} & {4} & {5} & {6} \\\\\n'.format(state[0].replace('_','\_'),'F','F',logic[0][0],logic[0][1],logic[0][2],logic[0][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} & {5} & {6} \\\\\n'.format(state[1].replace('_','\_'),'F','T',logic[1][0],logic[1][1],logic[1][2],logic[1][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} & {5} & {6} \\\\\n'.format(state[2].replace('_','\_'),'T','F',logic[2][0],logic[2][1],logic[2][2],logic[2][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} & {5} & {6} \\\\\n'.format(state[3].replace('_','\_'),'T','T',logic[3][0],logic[3][1],logic[3][2],logic[3][3]))
          self.f.write('\\bottomrule\n')
          self.f.write('\\end{tabular}\n')
          self.f.write('\\end{center}\n')
          self.f.write('Where \\newline\n')
          self.f.write('$A = {0}{1}{2}$\n'.format('\\texttt{',inputs[1].replace('_','\_'),'}\\newline'))
          self.f.write('$B = {0}{1}{2}$\n'.format('\\texttt{',inputs[0].replace('_','\_'),'}'))
        if len(inputs) == 1:
          self.f.write('\\begin{tabular}{@{}lccccc@{}}\n')
          self.f.write('\\toprule\n')
          self.f.write('Name & $A$ & LINAC & DIAG0 & HXU & SXU \\\\\n')
          self.f.write('\\midrule\n')
          self.f.write('{0} & {1} & {2} & {3} & {4} & {5} \\\\\n'.format(state[0].replace('_','\_'),'F',logic[0][0],logic[0][1],logic[0][2],logic[0][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} & {5} \\\\\n'.format(state[1].replace('_','\_'),'T',logic[1][0],logic[1][1],logic[1][2],logic[1][3]))
          self.f.write('\\bottomrule\n')
          self.f.write('\\end{tabular}\n')
          self.f.write('\\end{center}\n')
          self.f.write('Where \\newline\n')
          self.f.write('$A = {0}{1}{2}$\n'.format('\\texttt{',inputs[0].replace('_','\_'),'}'))


    def writeAnalogLogicTable(self,state,logic,inputs,title):
        self.f.write('{0}{1}{2}'.format('\\subsection{',title.replace('_',' ').replace('#','\#'),'}\n'))
        self.f.write('\\begin{center}\n')
        if len(state) == 2:
          self.f.write('\\begin{tabular}{@{}lcccccc@{}}\n')
          self.f.write('\\toprule\n')
          self.f.write('Name & LINAC & DIAG0 & HXU & SXU \\\\\n')
          self.f.write('\\midrule\n')
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[0].replace('_','\_'),logic[0][0],logic[0][1],logic[0][2],logic[0][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[1].replace('_','\_'),logic[1][0],logic[1][1],logic[1][2],logic[1][3]))
          self.f.write('\\bottomrule\n')
          self.f.write('\\end{tabular}\n')
          self.f.write('\\end{center}\n')
          self.f.write('Where \\newline\n')
          self.f.write('Fault $ = {0}{1}{2}$\n'.format('\\texttt{',inputs[0].replace('_','\_'),'}\\newline'))
        if len(state) == 3:
          self.f.write('\\begin{tabular}{@{}lcccc@{}}\n')
          self.f.write('\\toprule\n')
          self.f.write('Name & LINAC & DIAG0 & HXU & SXU \\\\\n')
          self.f.write('\\midrule\n')
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[0].replace('_','\_'),logic[0][0],logic[0][1],logic[0][2],logic[0][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[1].replace('_','\_'),logic[1][0],logic[1][1],logic[1][2],logic[1][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[2].replace('_','\_'),logic[2][0],logic[2][1],logic[2][2],logic[2][3]))
          self.f.write('\\bottomrule\n')
          self.f.write('\\end{tabular}\n')
          self.f.write('\\end{center}\n')
          self.f.write('Where \\newline\n')
          self.f.write('Fault $ = {0}{1}{2}$\n'.format('\\texttt{',inputs[0].replace('_','\_'),'}\\newline'))
        if len(state) == 9:
          self.f.write('\\begin{tabular}{@{}lcccc@{}}\n')
          self.f.write('\\toprule\n')
          self.f.write('Name & LINAC & DIAG0 & HXU & SXU \\\\\n')
          self.f.write('\\midrule\n')
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[0].replace('_','\_'),logic[0][0],logic[0][1],logic[0][2],logic[0][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[1].replace('_','\_'),logic[1][0],logic[1][1],logic[1][2],logic[1][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[2].replace('_','\_'),logic[2][0],logic[2][1],logic[2][2],logic[2][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[3].replace('_','\_'),logic[3][0],logic[3][1],logic[3][2],logic[3][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[4].replace('_','\_'),logic[4][0],logic[4][1],logic[4][2],logic[4][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[5].replace('_','\_'),logic[5][0],logic[5][1],logic[5][2],logic[5][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[6].replace('_','\_'),logic[6][0],logic[6][1],logic[6][2],logic[6][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[7].replace('_','\_'),logic[7][0],logic[7][1],logic[7][2],logic[7][3]))
          self.f.write('{0} & {1} & {2} & {3} & {4} \\\\\n'.format(state[8].replace('_','\_'),logic[8][0],logic[8][1],logic[8][2],logic[8][3]))
          self.f.write('\\bottomrule\n')
          self.f.write('\\end{tabular}\n')
          self.f.write('\\end{center}\n')
          self.f.write('Where \\newline\n')
          self.f.write('Fault $ = {0}{1}{2}$\n'.format('\\texttt{',inputs[0].replace('_','\_'),'}\\newline'))


    def startGroup(self, group):
        self.f.write('\\{0}{1}{2}\n'.format('chapter{Link Node Group ',group,'}'))

    def startLinkNode(self, id):
        self.f.write('\\{0}{1}{2}\n'.format('section{Link Node  ',id,'}'))

    def startApplication(self, id, ln):
        self.f.write('\\newpage\n')
        self.f.write('\\{0}{1}{2}{3}{4}\n'.format('section{Link Node ',ln,': Application Card ',id,'}'))

    def appCommunicationCheckoutTable(self):
        self.f.write('\\subsubsection{Communication}\n')
        self.f.write('\\begin{table}[H]\n')
        self.f.write('\\begin{tabular}{ l  c }\n')
        self.f.write('$\\Box$ & Toggle Application Enable \\\\\n')
        self.f.write('\\end{tabular}\n')
        self.f.write('\\end{table}\n')           

    def appCheckoutTable(self, crate, slot):
        self.f.write('\\begin{table}[H]\n')
        self.f.write('\\centering\n')
        self.f.write('\\makegapedcells\n')
        self.f.write('\\begin{tabularx}{\\textwidth}{| l | Y <{\\rule[0em]{0pt}{1em}}|}\n')
        self.f.write('{0}{1}-S{2}{3}\n'.format('\\multicolumn{2}{l}{',crate,slot,'}\\\\'))
        self.f.write('\\hline\n')
        self.f.write('Checkout completed by & \\\\\n')
        self.f.write('\\hline\n')
        self.f.write('Checkout date & \\\\\n')
        self.f.write('\\hline\n')
        self.f.write('\\end{tabularx}\n')
        self.f.write('\\end{table}\n')
        


    
