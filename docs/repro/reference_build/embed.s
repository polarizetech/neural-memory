    .section __DATA,__const
    .globl _binary_code_zip_start
    .globl _binary_code_zip_end
    .globl _binary_plotFunctions_py_start
    .globl _binary_plotFunctions_py_end
_binary_code_zip_start:
    .incbin "code.zip"
_binary_code_zip_end:
_binary_plotFunctions_py_start:
    .incbin "plotFunctions.py"
_binary_plotFunctions_py_end:
    .byte 0
