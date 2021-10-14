source /usr/local/lcls/package/anaconda/envs/python3.7env/bin/activate;
export PYTHONPATH=/usr/local/lcls/tools/python/toolbox;

mkdir ${2}working_tex

ls -v $1* > dictFileListInternal.txt

i=1
for file in $(cat dictFileListInternal.txt)
do
    echo Working on $file
    python mps_checkout_format.py -SrcFile=$file -LogFileLoc=${2}working_tex -LogFileName=$i -ErrorFile=$3
    i=${i}1
done

ls -v ${2}working_tex/* > texFileListInternal.txt

cat latex_header.tex >> ${2}MPS_Checkout_Report.tex

for texFile in $(cat texFileListInternal.txt)
do
    cat $texFile >> ${2}MPS_Checkout_Report.tex
done

echo '\end{document}' >> ${2}MPS_Checkout_Report.tex

rm dictFileListInternal.txt
rm texFileListInternal.txt
rm -rf ${2}working_tex
