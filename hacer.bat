
cls
python c\Capi.py build_ext --inplace
rem pause

copy s50info.* exe\
cd exe

pyinstaller s50info.spec
cd ..
