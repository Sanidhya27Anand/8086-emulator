
data_transfer_instr = ['MOV', 'XCHG', 'LEA', 'LDS', 'LES']
arithmetic_instr = ['ADD', 'ADC', 'SUB', 'SBB', 'INC', 'DEC', 'MUL', 'IMUL', 'DIV', 'IDIV', 'INC', 'DEC', 'CBW', 'CWD']
logical_instr = ['AND', 'OR', 'XOR', 'NOT', 'NEG', 'CMP', 'TEST']
rotate_shift_instr = ['RCL', 'RCR', 'ROL', 'ROR', 'SAL', 'SHL', 'SAR', 'SHR'] 
transfer_control_instr = ['LOOP', 'LOOPE', 'LOOPNE', 'LOOPNZ', 'LOOPZ', 'CALL', 'RET', 'RETF', 'JMP', 'JA', 'JAE', 'JB', 'JBE', 'JC', 'JCE', 'JCXZ', 'JE', 'JG', 'JGE', 'JL', 'JLE', 'JNA', 'JNAE', 'JNB', 'JNBE', 'JNC', 'JNE', 'JNG', 'JNE', 'JNG', 'JNGE', 'JNL', 'JNLE', 'JNO', 'JNP', 'JNS', 'JNZ', 'JO', 'JP', 'JPE', 'JPO', 'JS', 'JZ']
string_manipulation_instr = ['MOVSB', 'MOVSW', 'CMPSB', 'CMPSW', 'LODSB', 'LODSW', 'STOSB', 'STOSW', 'SCASB', 'SCASW', 'REP', 'REPE', 'REPZ', 'REPNE', 'REPNZ']
flag_manipulation_instr = ['STC', 'CLC', 'CMC', 'STD', 'CLD', 'STI', 'CLI', 'LANF', 'SANF']
stack_related_instr = ['PUSH', 'POP', 'PUSHF', 'POPF']
input_output_instr = ['IN', 'OUT']
miscellaneous_instr = ['NOP', 'INT', 'IRET', 'XLAT', 'HLT', 'ESC', 'INTO', 'LOCK', 'WAIT']
data_definition_instr = ['DB', 'DW', 'DD', 'DQ', 'DT', 'DUP']

conditional_jump_instr = [ 'JA', 'JAE', 'JB', 'JBE', 'JC', 'JCE', 'JCXZ', 'JE', 'JG', 'JGE', 'JL', 'JLE', 'JNA', 'JNAE', 'JNB', 'JNBE', 'JNC', 'JNE', 'JNG', 'JNE', 'JNG', 'JNGE', 'JNL', 'JNLE', 'JNO', 'JNP', 'JNS', 'JNZ', 'JO', 'JP', 'JPE', 'JPO', 'JS', 'JZ']

registers = ['AX', 'BX', 'CX', 'DX', 'AH', 'AL', 'BH', 'BL', 'CH', 'CL', 'DH', 'DL', 'CS', 'DS', 'SS', 'ES', 'SP', 'BP', 'SI', 'DI']

pseudo_instr = ['DB', 'DW', 'DD', 'DQ', 'DUP', 'PTR', 'LABEL', 'ALIGN', 'ORG', 'END', 'ASSUME', 'SEGMENT', 'NAME', 'TITLE', 'ENDS', 'SHORT', 'NEAR', 'FAR', 'SEG', 'OFFSET', 'TYPE']
