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
        self.f.write('{0}{1}{2}\n'.format('\\multicolumn{4}{l}{',shm,'}\\\\'))
        self.f.write('\\hline\n')
        self.f.write('Slot & App ID & Type & Description\\\\\n')
        self.f.write('\\hline\n')
        for slot in slots:
          self.f.write('{0} & {1} & {2} & {3} \\\\\n'.format(slot[0],slot[1],slot[2],slot[3]))
          self.f.write('\\hline\n')
        self.f.write('\\end{tabularx}\n')
        self.f.write('\\end{table}\n')

    def appendixA(self,lc1_id,shm,rack,slots):
        self.f.write('\\begin{table}[H]\n')
        self.f.write('\\centering\n')
        self.f.write('\\makegapedcells\n')
        self.f.write('\\begin{tabularx}{\\textwidth}{c c l | c c c c c}\n')
        self.f.write('{0}{1}{2}\n'.format('\\multicolumn{4}{l}{',shm,'}\\\\'))
        self.f.write('\\hline\n')
        self.f.write('Slot & App ID & PV Prefix & SW Version & FW Version & Enable & Initials & Date\\\\\n')
        self.f.write('\\hline\n')
        for slot in slots:
          self.f.write('{0} & {1} & {2}{3}{4} & & & & & \\\\\n'.format(slot[0],slot[1],'\\texttt{',slot[2],'}'))
          self.f.write('\\hline\n')
        self.f.write('\\end{tabularx}\n')
        self.f.write('\\end{table}\n')

    def writeAppInputs(self, inputs):
        self.f.write('\\begin{longtable}{@{}ccclcc@{}}\n')
        self.f.write('\\toprule\n')
        self.f.write('\\multicolumn{1}{@{}c}{App ID} & \\multicolumn{1}{c}{Slot}  & \\multicolumn{1}{c}{Channel} & \\multicolumn{1}{c@{}}{Input Name} & \\multicolumn{1}{c@{}}{LN Check} & \\multicolumn{1}{c@{}}{CN Check}\\\\\n')
        self.f.write('\\midrule\n')
        self.f.write('\\endfirsthead\n')
        self.f.write('\\multicolumn{6}{c}{\\ldots continued from previous page} \\\\\n')
        self.f.write('\\midrule\n')
        self.f.write('\\multicolumn{1}{@{}c}{App ID} & \\multicolumn{1}{c}{Slot}  & \\multicolumn{1}{c}{Channel}  & \\multicolumn{1}{c@{}}{Input Name} & \\multicolumn{1}{c@{}}{LN Check} & \\multicolumn{1}{c@{}}{CN Check}\\\\\n')
        self.f.write('\\midrule\n')
        self.f.write('\\endhead\n')
        self.f.write('\\midrule\n')
        self.f.write('\\multicolumn{6}{c}{continued on next page\\ldots} \\\\\n')
        self.f.write('\\endfoot\n')
        self.f.write('\\bottomrule\n')
        self.f.write('\\endlastfoot\n')
        for input in inputs:
          self.f.write('{0} & {1} & {2}{3}{4}{5}'.format(input[0],input[1],input[2],'& \\texttt{',input[4].replace('_','\_').replace('&','\&'),'} & $\Box$ & $\Box$\\\\\n'))
        self.f.write('\\end{longtable}\n')

    def writeLogicTable(self,format,header,rows,inputs):
        self.f.write('\\begin{center}\n')
        self.f.write(format)
        self.f.write('\\toprule\n')
        self.f.write(header)
        self.f.write('\\midrule\n')
        for row in rows:
          self.f.write(row)
        self.f.write('\\bottomrule\n')
        self.f.write('\\end{tabular}\n')
        self.f.write('\\end{center}\n')
        self.f.write('Where \\newline\n')
        for input in inputs:
          self.f.write(input)

    def startGroup(self, group):
        self.f.write('\\{0}{1}{2}\n'.format('chapter{Link Node Group ',group,'}'))

    def startLinkNode(self, id, location):
        self.f.write('\\{0}{1}{2}{3}{4}\n'.format('section{Link Node  ',id,': ',location,'}'))

    def startApplication(self, id, ln):
        self.f.write('\\newpage\n')
        self.f.write('\\{0}{1}{2}{3}{4}\n'.format('section{Link Node ',ln,': Application Card ',id,'}'))

    def startIgnoreGroup(self, title):
        self.f.write('\\newpage\n')
        self.f.write('\\{0}{1}{2}\n'.format('chapter{',title,'}'))

    def startFault(self, title):
        self.f.write('\\{0}{1}{2}\n'.format('section{',title,'}'))
        self.f.write('Checked By:\\\\\n')
        self.f.write('Date:\n')

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
        


    
