import subprocess
import os

class DocBook:
    file_name = 'docbook.xml'
    f = None
    tableHeaderColor='<?dbhtml bgcolor="#EE6060" ?><?dbfo bgcolor="#EE6060" ?>'
    tableRowColor=  ['<?dbhtml bgcolor="#EEEEEE" ?><?dbfo bgcolor="#EEEEEE" ?>',
                     '<?dbhtml bgcolor="#DDDDDD" ?><?dbfo bgcolor="#DDDDDD" ?>']

    def __init__(self, file_name):
        self.file_name = file_name
        self.f = open(file_name, "w")
        
    def exportHtml(self):
        cmd = 'xsltproc $PACKAGE_TOP/docbook-xsl/1.79.1/html/docbook.xsl {0} > {1}.html'.\
            format(self.file_name, self.file_name.split(".")[0])
        os.system(cmd)

    def exportPdf(self):
        print self.file_name + " -> " + self.file_name.split(".")[0]
        cmd = 'xsltproc $PACKAGE_TOP/docbook-xsl/1.79.1/fo/docbook.xsl {0} > {1}.fo'.\
            format(self.file_name, self.file_name.split(".")[0])
        os.system(cmd)

        cmd = 'fop -fo {0}.fo -pdf {0}.pdf'.format(self.file_name.split(".")[0])
        os.system(cmd)

        cmd = '\rm {0}.fo'.format(self.file_name.split(".")[0])
        os.system(cmd)

    def exportRtf(self):
        print self.file_name + " -> " + self.file_name.split(".")[0]
        cmd = 'xsltproc $PACKAGE_TOP/docbook-xsl/1.79.1/fo/docbook.xsl {0} > {1}.fo'.\
            format(self.file_name, self.file_name.split(".")[0])
        os.system(cmd)

        cmd = 'fop -fo {0}.fo -rtf {0}.rtf'.format(self.file_name.split(".")[0])
        os.system(cmd)

        cmd = '\rm {0}.fo'.format(self.file_name.split(".")[0])
        os.system(cmd)

    def writeHeader(self, title, first_name, last_name):
        self.f.write('<article xmlns="http://docbook.org/ns/docbook" version="5.0">\n')
        self.f.write('\n')
        self.f.write('<info>\n')
        self.f.write('   <title>{0}</title>\n'.format(title))
        self.f.write('   <author>\n')
        self.f.write('     <firstname>{0}</firstname><surname>{1}</surname>\n'.\
                         format(first_name, last_name))
        self.f.write('   </author>\n')
        self.f.write('</info>\n')

    def writeFooter(self):
        self.f.write('</article>\n')
        self.f.close()

    def openSection(self, title, anchor=None):
        self.f.write('<section>\n')
        if anchor != None: 
            self.f.write('<anchor id=\'{0}\'></anchor>\n'.format(anchor))
        self.f.write('<title>{0}</title>\n'.format(title))

    def closeSection(self):
        self.f.write('</section>\n')

    def para(self, text):
        self.f.write('<para>{0}</para>\n'.format(text))

    def table(self, title, cols, header, rows, table_id):
        if table_id != None:
            self.f.write('<table id="{0}" xreflabel="{1}">\n'.format(table_id, title))
        else:
            self.f.write('<table xreflabel="{0}">\n'.format(title))
        self.f.write('<title>{0}</title>\n'.format(title))
        self.f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(len(cols)))

        for i in range(0, len(cols)):
            self.f.write('<colspec colname=\'{0}\' colwidth="{1}"/>\n'.\
                             format(cols[i]['name'], cols[i]['width']))

        if header != None:
            self.f.write('<thead>\n')
            self.f.write(' <row>{0}\n'.format(self.tableHeaderColor))
            for i in range(0, len(header)):
                if header[i]['namest'] != None:
                    self.f.write('  <entry namest="{0}" nameend="{1}">{2}</entry>\n'.\
                                     format(header[i]['namest'], header[i]['nameend'], header[i]['name']))
                else:
                    self.f.write('  <entry>{0}</entry>\n'.format(header[i]['name']))
            self.f.write(' </row>\n')
            self.f.write('</thead>\n')
        rowIndex = 0

        self.f.write('<tbody>\n')
        for i in range(0, len(rows)):
            self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
            rowIndex=rowIndex+1
            for j in range(0, len(cols)):
                self.f.write('  <entry>{0}</entry>\n'.format(rows[i][j]))
            self.f.write('</row>\n')        
        self.f.write('</tbody>\n')
        self.f.write('</tgroup>\n')
        self.f.write('</table>\n')
