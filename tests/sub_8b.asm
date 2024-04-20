ASSUME CS:CODE , DS:DATA
CODE SEGMENT
START: 
    MOV AX,3H
    MOV BX,2H
    SUB AX,BX ; addition of two registers and it stores the result in AX
    HLT
    CODE ENDS
END START