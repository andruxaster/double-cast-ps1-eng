# Engine patch: word wrap for half-width (Latin/Cyrillic) text.
# Hook at 0x800289FC (text renderer, before the line-width check): when the current char is a space,
# measure the following word; if it does not fit into the line (struct+0x112), call the engine's
# newline routine 0x80028C04 and drop the space. Code lives in the body of the disabled
# half-width->SJIS converter (0x8002922C.., free after our 'jr ra' patch at 0x80029224).
HOOK_ADDR = 0x8002922c
HOOK_ASM = """
    andi $t0, $s1, 0xffff
    addiu $t1, $zero, 0x20
    bne $t0, $t1, done
    nop
    lw $t2, 0x170($sp)
    lhu $t3, 0x138($sp)
    addiu $t5, $zero, 0x24  # (load delay slot: must not use $t3 here)
    addiu $t3, $t3, 18      # space (6) + engine margin (12): usable width = +0x112 - 12
loop:
    lbu $t4, 0($t2)
    nop
    beq $t4, $zero, check
    nop
    beq $t4, $t1, check
    nop
    beq $t4, $t5, check
    sltiu $t6, $t4, 0x80
    bne $t6, $zero, half
    sltiu $t6, $t4, 0xa0
    beq $t6, $zero, notlead
    nop
    addiu $t3, $t3, 12
    b loop
    addiu $t2, $t2, 2
notlead:
    sltiu $t6, $t4, 0xe0
    bne $t6, $zero, half
    nop
    addiu $t3, $t3, 12
    b loop
    addiu $t2, $t2, 2
half:
    addiu $t3, $t3, 6
    b loop
    addiu $t2, $t2, 1
check:
    lh $t7, 0x112($s3)
    nop
    slt $t6, $t7, $t3
    beq $t6, $zero, done
    nop
    move $a0, $s3
    addiu $a1, $sp, 0x138
    addiu $a2, $sp, 0x13a
    jal 0x80028c04
    addiu $a3, $zero, 1
    bne $v0, $zero, 0x80028b84
    nop
    j 0x80028258
    nop
done:
    lh $v1, 0x116($s3)
    lh $v0, 0x134($s3)
    j 0x80028a04
    nop
"""
def assemble():
    import keystone
    ks = keystone.Ks(keystone.KS_ARCH_MIPS, keystone.KS_MODE_MIPS32 + keystone.KS_MODE_LITTLE_ENDIAN)
    enc, _ = ks.asm(HOOK_ASM, HOOK_ADDR)
    return bytes(enc)
