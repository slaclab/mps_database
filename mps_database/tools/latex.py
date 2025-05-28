import subprocess
import os

class Latex:
    file_name = 'latex.tex'

    def __init__(self,file_name):
        self.file_name = file_name
        self.f = open(file_name,'w')

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
        self.f.write('\\documentclass[10pt, twoside]{article}\n')
        self.f.write('\\usepackage{lcls-article}\n')
        self.f.write('\\newcommand\code{\\begingroup \\urlstyle{tt}\\Url}\n')
        self.f.write('\\renewcommand\\revnum{0}{1}{2}'.format('{',version,'}\n'))
        self.f.write('\\title{0}{1}{2}'.format('{',title,'}\n'))
        self.f.write('\\author{\\revnum}\n')
        self.f.write('\\begin{document}\n')
        self.f.write('\\maketitle\n')
        self.f.write('\\tableofcontents\n')
        self.f.write('\\newpage\n')

    def endDocument(self, report_path):
        self.f.write('\\end{document}\n')
        self.f.close()
        self.exportPdf(report_path)

    def crateProfile(self,lc1_id, shm, rack, slots):
        self.f.write('\\begin{table}[H]\n')
        self.f.write('\\centering\n')
        self.f.write('\\makegapedcells\n')
        self.f.write('\\begin{tabular}{|c c c|}\n')
        self.f.write('{0}{1}{2}\n'.format('\\multicolumn{3}{l}{',shm,'}\\\\'))
        self.f.write('\\hline\n')
        self.f.write('Slot & App ID & Type\\\\\n')
        self.f.write('\\hline\n')
        for slot in slots:
          self.f.write('{0} & {1} & {2} \\\\\n'.format(slot[0],slot[1],slot[2]))
          self.f.write('\\hline\n')
        self.f.write('\\end{tabular}\n')
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
        self.f.write('\\{0}{1}{2}\n'.format('section{Link Node Group ',group,'}'))

    def startIgnoreGroup(self, title):
        self.f.write('\\newpage\n')
        self.f.write('\\{0}{1}{2}\n'.format('chapter{',title,'}'))

    def startFault(self, title):
        self.f.write('\\{0}{1}{2}\n'.format('section{',title,'}'))       

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
        


    
