## This python script needs the astor package to work <br/> do `pip install astor` in the command line/powershell
<br/>
Based on https://github.com/dantarion/bbtools, this version updates the code to python 3 and astor to its latest version. 

**Other changes include:** <br/>
database update <br/>
asterror fixes <br/>
auto upon and slot naming in commands <br/>
support for character specific slots and upons <br/>
case insensitivity for commands within the main functions<br/>
and fixes for various other command related bugs <br/>

## Details
### Case insensitivity
Python syntax stays case sensitive, like `if`, `else`, `def`, `not` etc
```
@State                  <-- Case insensitive 
def NmlAtk6D():         !!! <-- Case sensitive

    def upon_IMmeDIaTE():           <-- Case insensitive
        Attackdefaults_StanDInGNormal()         <-- Case insensitive
        AttackLevel_(4)
        Damage(350)
        AirUntechableTime(60)
        AttackP2(100)
        ...

        def upon_STATE_END():
            SetZVal(0)

        def upon_OPPONENT_HIT():
            clearUponHandler(OppONENT_HIT)      <-- OPPONENT_HIT case insensitive
            if SLOT_19 <= 400000:           
                AirPushbackY(8000)
                PushbackX(-6000)
                if SLOT_51:
                    enterState('AN_NmlAtk6DExeOD')          !!! <-- 'AN_NmlAtk6DExeOD' case sensitive
                else:
                    enterState('AN_NmlAtk6DExe')
        if SLOT_OverDRiveTiMer:                 <-- SLOT_OverdriveTimer case insensitive
            SLOT_51 = 1
    sprite('tm214_00', 3)              !!! <-- 'tm214_00' case sensitive
    sprite('tm214_01', 3)
    sprite('tm214_02', 3)
    ...
```

### How to use character specific slot and upon
A json file using the character's code is searched in the `static_db/XXX/(slot_db and upon_db)/` directory, `global.json` is required and will be searched first, then if the character file exists, the character json will be applied over <br/>
Example: Terumi uses `tm` as his character code, so the script will look for `tm.json`

Do remember that the overwritten slot/upon will no longer refer to their corresponding global number, which can break rebuilding
