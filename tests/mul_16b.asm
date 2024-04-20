ASSUME CS:CODE , DS:DATA
DATA SEGMENT 
    N1 DW 1234H
    N2 DW 1010H
DATA ENDS 
     CODE SEGMENT    
  
  START:
        MOV AX,DATA 
        MOV DS,AX
                                      
                                      
        MOV AX,N1
        MOV BX,N2
        
        MUL BX        
    CODE ENDS 
ENDS START