import os, struct, json, sys, astor
from ast import *

GAME = "BBCF"

pypath = os.path.dirname(sys.argv[0])
json_data = open(os.path.join(pypath, "static_db/" + GAME + "/command_db.json")).read()
command_db = json.loads(json_data)
json_data = open(os.path.join(pypath, "static_db/" + GAME + "/named_values/move_inputs.json")).read()
move_inputs = json.loads(json_data)
json_data = open(os.path.join(pypath, "static_db/" + GAME + "/named_values/normal_inputs.json")).read()
normal_inputs = json.loads(json_data)
json_data = open(os.path.join(pypath, "static_db/" + GAME + "/named_values/hit_animation.json")).read()
animation_db = json.loads(json_data)
json_data = open(os.path.join(pypath, "static_db/" + GAME + "/upon_db/global.json")).read()
upon_db = json.loads(json_data)
json_data = open(os.path.join(pypath, "static_db/" + GAME + "/slot_db/global.json")).read()
slot_db = json.loads(json_data)
json_data = open(os.path.join(pypath, "static_db/" + GAME + "/object_db/global.json")).read()
object_db = json.loads(json_data)
#Checking for a custom slot/upon db
character_name = sys.argv[1].replace("scr_", "").split(".")[0]
if character_name[:-2] == "ea" and len(character_name) > 2:
    character_name = character_name[:-2]
try:
    upon_db.update(json.loads(open(os.path.join(pypath, "static_db/" + GAME + "/upon_db/" + character_name + ".json")).read()))
except IOError:
    pass
try:
    slot_db.update(json.loads(open(os.path.join(pypath, "static_db/" + GAME + "/slot_db/" + character_name + ".json")).read()))
except IOError:
    pass

MODE = "<"

def get_operation(operation_id):
    if operation_id == 0:
        op = Add()
    elif operation_id == 1:
        op = Sub()
    elif operation_id == 2:
        op = Mult()
    elif operation_id == 3:
        op = Div()
    elif operation_id == 4:
        op = Mod()
    elif operation_id == 5:
        op = And()
    elif operation_id == 6:
        op = Or()
    elif operation_id == 7:
        op = And()
    elif operation_id == 8:
        op = Or()
    elif operation_id == 9:
        op = Eq()
    elif operation_id == 10:
        op = Gt()
    elif operation_id == 11:
        op = Lt()
    elif operation_id == 12:
        op = GtE()
    elif operation_id == 13:
        op = LtE()
    else:
        raise Exception("Unvalid operation_id" + str(operation_id))
    
    return op

def slot_handler(command, cmd_data):
    command = str(command)
    tmp = []
    for i, v in enumerate(cmd_data):
        if i in command_db[command]['type']:
            continue
        elif i-1 in command_db[command]['type']:
            if cmd_data[i-1] == 0:
                tmp.append(Constant(v))
            else:
                tmp.append(Name(get_slot_name(v)))
        else:
            tmp.append(Constant(v))
            
    return tmp

def find_named_value(command, value):
    str_value = str(value)
    if command in [43, 14012]:
        if str_value in move_inputs:
            return move_inputs[str_value]
    elif command == 14001:
        if str_value in normal_inputs['grouped_values']:
            return normal_inputs['grouped_values'][str_value]
        s = struct.pack('>H', value)
        button_byte, dir_byte = struct.unpack('>BB', s)
        if str(button_byte) in normal_inputs['button_byte'] and str(dir_byte) in normal_inputs['direction_byte']:
            return normal_inputs['direction_byte'][str(dir_byte)] + normal_inputs['button_byte'][str(button_byte)]
    return hex(value)

def get_animation_name(cmd_data):
    str_value = str(cmd_data)
    if str_value in animation_db:
        return animation_db[str_value]
    return cmd_data

def get_upon_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in upon_db:
        str_cmd_data = upon_db[str_cmd_data]
    return "upon_" + str_cmd_data


def get_slot_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in slot_db:
        str_cmd_data = slot_db[str_cmd_data]
    return "SLOT_" + str_cmd_data

# Not used yet
def get_object_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in object_db:
        str_cmd_data = object_db[str_cmd_data]
    return str_cmd_data

# Changes numbers to their db value
def sanitizer(command):
    def sanitize(values):
        i = values[0]
        value = values[1]
        if command in [43, 14001, 14012] and isinstance(value, int):
            return Name(find_named_value(command, value))
        elif command in [17, 29, 30] and i == 0:
            return Name(get_upon_name(value))
        elif command in [21007] and i == 1:
            return Name(get_upon_name(value))
        elif command in [9322, 9324, 9334, 9336]:
            return Name(get_animation_name(value))
        elif command and not isinstance(value, str) and "hex" in command_db[str(command)]:
            return Name(hex(value))
        return Constant(value)

    return sanitize


def function_clean(command):
    command = command.replace("-", "__ds__").replace("@", "__at__").replace("?", "__qu__").replace(" ", "__sp__")
    if command[0].isdigit():
        command = "__" + command
    return command


def parse_bbscript_routine(file):
    ast_root = Module([], [])
    ast_stack = [ast_root.body]
    empty_args = arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[])
    astor_handler = []
    file.seek(0, os.SEEK_END)
    end = file.tell()
    file.seek(0)
    FUNCTION_COUNT, = struct.unpack(MODE + "I", file.read(4))
    file.seek(4 + 0x24 * FUNCTION_COUNT)
    # Going through the bin
    while file.tell() != end:
        loc = file.tell()  # Debug
        current_cmd, = struct.unpack(MODE + "I", file.read(4))
        db_data = command_db[str(current_cmd)]
        if "name" not in db_data:
            db_data["name"] = "Unknown{0}".format(current_cmd)
        if "format" not in command_db[str(current_cmd)]:
            cmd_data = [file.read(command_db[str(current_cmd)]["size"] - 4)]
        else:
            cmd_data = list(struct.unpack(MODE + db_data["format"], file.read(struct.calcsize(db_data["format"]))))
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
            if len(ast_stack) > 1:
                ast_stack.pop()
            ast_stack[-1].append(FunctionDef(function_clean(cmd_data[0]), empty_args, [], [Name(id="State")]))
            ast_stack.append(ast_stack[-1][-1].body)
        # 8 is startSubroutine
        elif current_cmd == 8:
            if len(ast_stack) > 1:
                ast_stack.pop()
            ast_stack[-1].append(FunctionDef(function_clean(cmd_data[0]), empty_args, [], [Name(id="Subroutine")]))
            ast_stack.append(ast_stack[-1][-1].body)
        # 15 is upon
        elif current_cmd == 15:
            ast_stack[-1].append(
                FunctionDef(get_upon_name(cmd_data[0]), empty_args, [], []))
            ast_stack.append(ast_stack[-1][-1].body)
        # 4 is if
        elif current_cmd == 4:
            if cmd_data[1] == 0:
                try: 
                    if ast_stack[-1][-1]:
                        arcsysdoubleifspaghetti = ast_stack[-1][-1]
                except IndexError:
                    arcsysdoubleifspaghetti = True
                if isinstance(arcsysdoubleifspaghetti, Expr):
                    try: 
                        tmp = lastExpr.value
                        ast_stack[-1].append(If(tmp, [], []))
                        ast_stack.append(ast_stack[-1][-1].body)
                        ast_stack[-2].pop(-2)
                    except Exception:
                        print("Tell Morph to fix his script")
                        tmp = Name(get_slot_name(0))
                        ast_stack[-1].append(If(tmp, [], []))
                        ast_stack.append(ast_stack[-1][-1].body)
                else:
                    ast_stack[-1].append(If(Name(get_slot_name(cmd_data[1]))))
                    ast_stack.append(ast_stack[-1][-1].body)
            else:
                tmp = Name(get_slot_name(cmd_data[1]))
                ast_stack[-1].append(If(tmp, [], []))
                ast_stack.append(ast_stack[-1][-1].body)
        # 54 is ifNot
        elif current_cmd == 54:
            if cmd_data[1] == 0:
                try:
                    if ast_stack[-1][-1]:
                        arcsysdoubleifspaghetti = ast_stack[-1][-1]
                except IndexError:
                    arcsysdoubleifspaghetti = True
                if isinstance(arcsysdoubleifspaghetti, Expr):
                    try:
                        tmp = lastExpr.value
                        ast_stack[-1].append(If(UnaryOp(Not(), tmp), [], []))
                        ast_stack.append(ast_stack[-1][-1].body)
                        ast_stack[-2].pop(-2)
                    except Exception:
                        print("Tell Morph to fix his script")
                        tmp = Name(get_slot_name(0))
                        ast_stack[-1].append(If(UnaryOp(Not(), tmp), [], []))
                        ast_stack.append(ast_stack[-1][-1].body)
            else:
                tmp = Name(get_slot_name(cmd_data[1]))
                ast_stack[-1].append(If(UnaryOp(Not(), tmp), [], []))
                ast_stack.append(ast_stack[-1][-1].body)
        # 56 is else
        elif current_cmd == 56:
            ifnode = ast_stack[-1][-1]
            ast_stack.append(ifnode.orelse)
        # 18 is ifSlotSendTolabel
        elif current_cmd == 18:
            if cmd_data[2] == 0:
                tmp = lastExpr.value
                ast_stack[-1].append(If(tmp, [], []))
                ast_stack[-1].pop(-2)
            else:
                tmp = Name(get_slot_name(cmd_data[2]))
                ast_stack[-1].append(If(tmp, [], []))
            ast_stack[-1][-1].body.append(Expr(Call(Name(id=db_data["name"]), [Constant(cmd_data[0])], [])))
        # 19 is ifNotSlotSendTolabel
        elif current_cmd == 19:
            if cmd_data[2] == 0:
                tmp = lastExpr.value
                ast_stack[-1].append(If(UnaryOp(Not(), tmp), [], []))
                ast_stack[-1].pop(-2)
            else:
                tmp = Name(get_slot_name(cmd_data[2]))
                ast_stack[-1].append(If(UnaryOp(Not(), tmp), [], []))
            ast_stack[-1][-1].body.append(Expr(Call(Name(id=db_data["name"]), [Constant(cmd_data[0])], [])))
        # 35 is apply function to Object
        elif current_cmd == 36:
            ast_stack[-1].append(
                FunctionDef(db_data["name"] + "_" + str(cmd_data[0]), empty_args, [], []))
            ast_stack.append(ast_stack[-1][-1].body)
        # 40 is operation stored in SLOT_0
        elif current_cmd == 40:
            cmd_data = slot_handler(current_cmd, cmd_data)
            cmd_data[0] = cmd_data[0].value
            lval = cmd_data[1]
            rval = cmd_data[2]
            op = get_operation(cmd_data[0])
            if cmd_data[0] in [0, 1, 2, 3]:
                lastExpr = BinOp(lval, op, rval)
            elif cmd_data[0] in [4]:
                lastExpr = Expr(BinOp(lval, op, rval))
            elif cmd_data[0] in [5, 6]:
                lastExpr = Expr(BoolOp(op, [UnaryOp(Not(), lval), UnaryOp(Not(),rval)]))
            elif cmd_data[0] in [7, 8]:
                lastExpr = Expr(BoolOp(op, [lval, rval]))
            elif cmd_data[0] in [9, 10, 11, 12, 13]:
                lastExpr = Expr(Compare(lval, [op], [rval]))
            else:
                raise Exception("Unhandled operation")
            ast_stack[-1].append(lastExpr)
        # 41 is StoreValue, assigning to SLOT
        elif current_cmd == 41:
            cmd_data = slot_handler(current_cmd, cmd_data)
            lval = cmd_data[0]
            rval = cmd_data[1]
            tmp = Assign([lval], rval)
            ast_stack[-1].append(tmp)
        # 47 slot operation saved to slot diff from SLOT_0
        elif current_cmd == 47:
            cmd_data = slot_handler(current_cmd, cmd_data)
            cmd_data[0] = cmd_data[0].value
            aval = cmd_data[1]
            lval = cmd_data[2]
            rval = cmd_data[3]
            op = get_operation(cmd_data[0])
            if cmd_data[0] in [0, 1, 2, 3]:
                tmp = BinOp(lval, op, rval)
            elif cmd_data[0] in [4]:
                tmp = Expr(BinOp(lval, op, rval))
            elif cmd_data[0] in [5, 6]:
                tmp = Expr(BoolOp(op, [UnaryOp(Not(), lval), UnaryOp(Not(),rval)]))
            elif cmd_data[0] in [7, 8]:
                tmp = Expr(BoolOp(op, [lval, rval]))
            elif cmd_data[0] in [9, 10, 11, 12, 13]:
                tmp = Expr(Compare(lval, [op], [rval]))
            else:
                raise Exception("Unhandled operation")
            tmp = Assign([aval], tmp)
            ast_stack[-1].append(tmp)
            
        # 49 is ModifyVar_
        elif current_cmd == 49:
            cmd_data = slot_handler(current_cmd, cmd_data)
            cmd_data[0] = cmd_data[0].value
            lval = cmd_data[1]
            rval = cmd_data[2]
            op = get_operation(cmd_data[0])
            tmp = Assign([lval], BinOp(lval, op, rval))
            ast_stack[-1].append(tmp)
        elif current_cmd in [11058, 22019]:
            attributes = ""
            if cmd_data[0] == 1:
                attributes += "H"
            if cmd_data[1] == 1:
                attributes += "B"
            if cmd_data[2] == 1:
                attributes += "F"
            if cmd_data[3] == 1:
                attributes += "P"
            if cmd_data[4] == 1:
                attributes += "T"
            ast_stack[-1].append(
                Expr(Call(Name(id=db_data["name"]), args=[Constant(attributes)], keywords=[])))
        # Indentation end
        elif current_cmd in [1, 5, 9, 16, 35, 55, 57]:
            if len(ast_stack[-1]) == 0:
                ast_stack[-1].append(Pass())
            if len(ast_stack) > 1:
                astor_handler = ast_stack.pop()
            else:
                ast_stack[-1][-1].body.append(
                    Expr(Call(Name(id=db_data["name"]), args=list(map(sanitizer(current_cmd), enumerate(cmd_data))), keywords=[])))
        else:
            # Things that affect slot_0
            if current_cmd in [39, 40, 42, 43, 44, 45, 46, 61, 23036, 23037, 23145, 23146, 23148, 23156, 23166]:
                lastExpr = Expr(Call(Name(id=db_data["name"]), args=list(map(sanitizer(current_cmd), enumerate(cmd_data))), keywords=[]))
                
            if len(ast_stack) == 1:
                ast_stack.append(astor_handler)
            if 'type' not in command_db[str(current_cmd)]:
                ast_stack[-1].append(
                    Expr(Call(Name(id=db_data["name"]), args=list(map(sanitizer(current_cmd), enumerate(cmd_data))), keywords=[])))
            else:
                ast_stack[-1].append(
                    Expr(Call(Name(id=db_data["name"]), args=slot_handler(current_cmd, cmd_data), keywords=[])))
                
    return ast_root

def parse_bbscript(filename, output_path):
    file = open(filename, 'rb')
    ast_root = parse_bbscript_routine(file)
    output = os.path.join(output_path, os.path.split(filename)[1].split('.')[0] + ".py")
    py = open(output, "w", encoding="utf-8")
    py.write(astor.to_source(ast_root))
    py.close()


if __name__ == '__main__':
    if len(sys.argv) not in [2, 3] or sys.argv[1].split(".")[-1] != "bin":
        print("Usage:BBCF_Script_Parser.py scr_xx.bin outdir")
        print("Default output directory if left blank is the input file's directory.")
        sys.exit(1)
    if len(sys.argv) == 2:
        parse_bbscript(sys.argv[1], os.path.split(sys.argv[1])[0])
    else:
        parse_bbscript(sys.argv[1], sys.argv[2])
    print("\033[96m" + "complete" + "\033[0m")
