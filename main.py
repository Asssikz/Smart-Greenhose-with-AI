pibody = 'outer'

if pibody == 'outer':
    from OuterPico.outer import main_loop
elif pibody == 'inner':
    from InnerPico.inner import main_loop

while True:
    main_loop()