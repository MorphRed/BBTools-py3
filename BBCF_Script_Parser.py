import os, struct, json, astor, sys
from ast import *

pypath = os.path.dirname(sys.argv[0])
json_data = open(os.path.join(pypath, "Static_DB/BBCF/CommandDB.json")).read()
command_db = json.loads(json_data)
json_data = open(os.path.join(pypath, "Static_DB/BBCF/Named_Values/Move_Inputs.json")).read()
move_inputs = json.loads(json_data)
json_data = open(os.path.join(pypath, "Static_DB/BBCF/Named_Values/Normal_Inputs.json")).read()
normal_inputs = json.loads(json_data)
MODE = "<"
GAME = "bb"
ast_root = Module([], [])
empty_args = arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[])
# placeholder for a real upon lookup idk
upon_db = {
    "0": "IMMEDIATE",
    "1": "STATE_END",
    "2": "LANDING",
    "10": "ON_HIT_OR_BLOCK"
}

slot_db = {
    "47": "IsInOverdrive",
    "54": "IsInOverdrive2",
    "106": "IsInOverdrive3",
    "91": "IsPlayer2",
    "112": "IsUnlimitedCharacter"
}


def find_named_value(command, value):
    str_value = str(value)
    if command in [14012, 43]:
        if str_value in move_inputs:
            return move_inputs[str_value]

    elif command == 14001:
        if str_value in normal_inputs['grouped_values']:
            return normal_inputs['grouped_values'][str_value]
        s = struct.pack('>H', value)
        button_byte, dir_byte = struct.unpack('>BB', s)
        if str(button_byte) in normal_inputs['buttonbyte'] and str(dir_byte) in normal_inputs['directionbyte']:
            return normal_inputs['directionbyte'][str(dir_byte)] + normal_inputs['buttonbyte'][str(button_byte)]
    return hex(value)


def get_upon_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in upon_db:
        return upon_db[str_cmd_data]
    return str_cmd_data


def get_slot_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in slot_db:
        return slot_db[str_cmd_data]
    return str_cmd_data


# Removes filler hex and converts hex inputs for AST
def sanitizer(command):
    def sanitize(s):
        if command in [43, 14012, 14001] and isinstance(s, int):
            return Name(find_named_value(command, s))
        elif command and not isinstance(s, str) and "hex" in command_db[str(command)]:
            return Name(hex(s))
        return Constant(s)

    return sanitize


def function_clean(command):
    for i, v in enumerate(command):
        if "-" in v:
            command[i] = v.replace("-", "__ds__")
        if "@" in v:
            command[i] = v.replace("@", "__at__")
        if "?" in v:
            command[i] = v.replace("?", "__qu__")
        if " " in v:
            command[i] = v.replace(" ", "__sp__")
        if v[:1].isdigit():
            command[i] = "__" + v


def parse_bbscript_routine(f, end=-1):
    current_indicator = "_PRE"
    astor_handler = []
    ast_stack = [ast_root.body]

    # Going through the bin
    while f.tell() != end:
        loc = f.tell()  # Debug
        current_cmd, = struct.unpack(MODE + "I", f.read(4))
        db_data = command_db[str(current_cmd)]
        if "name" not in db_data:
            db_data["name"] = "Unknown{0}".format(current_cmd)
        if "format" not in command_db[str(current_cmd)]:
            cmd_data = [f.read(command_db[str(current_cmd)]["size"] - 4)]
        else:
            cmd_data = list(struct.unpack(MODE + db_data["format"], f.read(struct.calcsize(db_data["format"]))))
        # Cleaning up the binary string
        for i, v in enumerate(cmd_data):
            if isinstance(v, bytes):
                try:
                    cmd_data[i] = v.decode().strip("\x00")
                except UnicodeDecodeError:
                    # Handles unicode bug if it happens, eg kk400_13
                    v = v.strip(b"\x00")
                    debug = ''
                    for j in v:
                        debug += chr(j)
                    cmd_data[i] = debug

        # AST STUFF
        # 0 is startState
        if current_cmd == 0:
            function_clean(cmd_data)
            current_indicator = cmd_data[0]
            if len(ast_stack) > 1:
                ast_stack.pop()
            ast_stack[-1].append(FunctionDef(current_indicator, empty_args, [], ["State"]))
            ast_stack.append(ast_stack[-1][-1].body)
        # 8 is startSubroutine
        elif current_cmd == 8:
            function_clean(cmd_data)
            current_indicator = cmd_data[0]
            if len(ast_stack) > 1:
                ast_stack.pop()
            ast_stack[-1].append(FunctionDef(current_indicator, empty_args, [], ["Subroutine"]))
            ast_stack.append(ast_stack[-1][-1].body)
        # 15 is upon
        elif current_cmd == 15:
            ast_stack[-1].append(
                FunctionDef(db_data['name'] + "_" + get_upon_name(cmd_data[0]), empty_args, [], []))
            ast_stack.append(ast_stack[-1][-1].body)
        # 4 is if
        elif current_cmd == 4:
            if cmd_data[1] == 0:
                if not ast_stack[-1]:
                    tmp = Name(id="SLOT_" + get_slot_name(cmd_data[1]))
                    ast_stack[-1].append(If(tmp, [], []))
                else:
                    tmp = ast_stack[-1].pop()
                    if isinstance(tmp, Expr):
                        tmp = tmp.value
                        ast_stack[-1].append(If(tmp, [], []))
                    else:
                        ast_stack[-1].append(tmp)
            else:
                tmp = Name(id="SLOT_" + get_slot_name(cmd_data[1]))
                ast_stack[-1].append(If(tmp, [], []))
            ast_stack.append(ast_stack[-1][-1].body)
        # 18 is 
        elif current_cmd == 18:
            if cmd_data[1] == 0:
                tmp = ast_stack[-1].pop()
                if isinstance(tmp, Expr):
                    tmp = tmp.value
            else:
                tmp = Name(id="SLOT_" + get_slot_name(cmd_data[2]))
            ast_stack[-1].append(If(tmp, [], []))
            ast_stack[-1][-1].body = [Expr(Call(Name(id="_gotolabel"), [Constant(cmd_data[0])], []))]
        # 40 is operation type
        elif current_cmd == 40 and cmd_data[0] in [9, 10, 11, 12, 13]:
            if cmd_data[1] == 2:
                lval = Name(id="SLOT_" + str(cmd_data[2]))
            else:
                lval = Constant(cmd_data[2])
            if cmd_data[3] == 2:
                rval = Name(id="SLOT_" + str(cmd_data[4]))
            else:
                rval = Constant(cmd_data[4])
            if cmd_data[0] == 9:
                op = Eq()
            if cmd_data[0] == 10:
                op = Gt()
            if cmd_data[0] == 11:
                op = Lt()
            if cmd_data[0] == 12:
                op = GtE()
            if cmd_data[0] == 13:
                op = LtE()
            tmp = Expr(Compare(lval, [op], [rval]))
            ast_stack[-1].append(tmp)
        # 41 is StoreValue
        elif current_cmd == 41:
            if cmd_data[0] == 2:
                lval = Name(id="SLOT_" + str(cmd_data[1]))
            else:
                lval = Constant(cmd_data[1])
            if cmd_data[2] == 2:
                rval = Name(id="SLOT_" + str(cmd_data[3]))
            else:
                rval = Constant(cmd_data[3])
            tmp = Assign([lval], rval)
            ast_stack[-1].append(tmp)
        # 49 is ModifyVar_
        elif current_cmd == 49 and cmd_data[0] in [0, 1, 2, 3]:
            if cmd_data[1] == 2:
                lval = Name(id="SLOT_" + str(cmd_data[2]))
            else:
                lval = Constant(cmd_data[2])
            if cmd_data[3] == 2:
                rval = Name(id="SLOT_" + str(cmd_data[4]))
            else:
                rval = Constant(cmd_data[4])
            if cmd_data[0] == 0:
                op = Add()
            if cmd_data[0] == 1:
                op = Sub()
            if cmd_data[0] == 2:
                op = Mult()
            if cmd_data[0] == 3:
                op = Div()
            tmp = Assign([lval], BinOp(lval, op, rval))
            ast_stack[-1].append(tmp)
        # 54 is ifNot
        elif current_cmd == 54:
            if cmd_data[1] == 0:
                i = 1
                tmp = ast_stack[-1]
                # In case the Expr isn't directly behind the if not
                while not isinstance(tmp, Expr):
                    tmp = ast_stack[-1][-i]
                    i = i + 1
                tmp = tmp.value
                ast_stack[-1].append(If(UnaryOp(Not(), tmp), [], []))
                ast_stack.append(ast_stack[-1][-1].body)
                ast_stack[-2].pop(-i)
            else:
                tmp = Name(id="SLOT_" + get_slot_name(cmd_data[1]))
                ast_stack[-1].append(If(UnaryOp(Not(), tmp), [], []))
                ast_stack.append(ast_stack[-1][-1].body)
        # 56 is else
        elif current_cmd == 56:
            ifnode = ast_stack[-1][-1]
            ast_stack.append(ifnode.orelse)
        elif current_cmd in [1, 5, 9, 16, 55, 57]:
            if len(ast_stack[-1]) == 0:
                ast_stack[-1].append(Pass())
            if len(ast_stack) > 1:
                astor_handler = ast_stack.pop()
            else:
                ast_stack[-1][-1].body.append(
                    Expr(Call(Name(id=db_data["name"]), list(map(sanitizer(current_cmd), cmd_data)), [])))
        else:
            if len(ast_stack) == 1:
                ast_stack.append(astor_handler)
            ast_stack[-1].append(
                Expr(Call(Name(id=db_data["name"]), list(map(sanitizer(current_cmd), cmd_data)), [])))


def parse_bbscript(f, filename, filesize):
    BASE = f.tell()
    out_path, out_name = os.path.split(filename)
    out_name = out_name[:-4] + ".py"
    if len(sys.argv) == 3:
        out_path = sys.argv[2]
    output = os.path.join(out_path, out_name)
    FUNCTION_COUNT, = struct.unpack(MODE + "I", f.read(4))
    f.seek(BASE + 4 + 0x24 * FUNCTION_COUNT)
    parse_bbscript_routine(f, filesize)
    py = open(output, "w")
    py.write(astor.to_source(ast_root))
    py.close()


if __name__ == '__main__':
    if len(sys.argv) not in [2, 3]:
        print("Usage:BBCF_Script_Parser.py scr_xx.bin outdir")
        print("Default output directory if left blank is the input file's directory.")
    else:
        file = open(sys.argv[1], 'rb')
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        parse_bbscript(file, file.name, size)
        print("complete")
