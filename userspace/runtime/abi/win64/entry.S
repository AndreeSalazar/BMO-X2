.text
.globl bmo_win64_start
bmo_win64_start:
    # The loader supplies an aligned initial stack, without a return address.
    sub $32, %rsp
    call bmo_main
    ud2
