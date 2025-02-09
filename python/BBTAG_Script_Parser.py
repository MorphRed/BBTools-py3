import os, struct, json, sys, astor
from ast import *

GAME = "BBTAG"

pypath = os.path.dirname(sys.argv[0])
json_data = open(os.path.join(pypath, "static_db/" + GAME + "/command_db.json")).read()
command_db = json.loads(json_data)
json_data = open(os.path.join(pypath, "static_db/" + GAME + "/named_values/move_inputs.json")).read()
move_inputs = json.loads(json_data)
json_data = open(os.path.join(pypath, "static_db/" + GAME + "/named_values/normal_inputs.json")).read()
normal_inputs = json.loads(json_data)
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


def get_upon_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in upon_db:
        str_cmd_data = upon_db[str_cmd_data]
    return "upon_" + str_cmd_data


def get_slot_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in slot_db:
        str_cmd_data = slot_db[str_cmd_data]
    return Name(id="SLOT_" + str_cmd_data)

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
        elif command in [17, 29, 30, 21007] and i == 0:
            return Name(get_upon_name(value).replace("upon_", ""))
        elif command and not isinstance(value, str) and "hex" in command_db[str(command)]:
            return Name(hex(value))
        return Constant(value)

    return sanitize


def function_clean(command):
    if "-" in command:
        command = command.replace("-", "__ds__")
    if "@" in command:
        command = command.replace("@", "__at__")
    if "?" in command:
        command = command.replace("?", "__qu__")
    if " " in command:
        command = command.replace(" ", "__sp__")
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
                        tmp = get_slot_name(0)
                        ast_stack[-1].append(If(tmp, [], []))
                        ast_stack.append(ast_stack[-1][-1].body)
                else:
                    ast_stack[-1].append(If(get_slot_name(cmd_data[1])))
                    '''
                    ast_stack[-1][-1] = If(
                        BoolOp(op=Or(), values=[
                            BoolOp(op=And(), values=[Name(ast_stack[-1][-1].test.id), ast_stack[-1][-1].body[0].value]), 
                            BoolOp(op=And(), values=[UnaryOp(Not(), Name(ast_stack[-1][-1].test.id)), ast_stack[-1][-1].orelse[0].value])]))
                    '''
                    ast_stack.append(ast_stack[-1][-1].body)
            else:
                tmp = get_slot_name(cmd_data[1])
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
                        tmp = get_slot_name(0)
                        ast_stack[-1].append(If(UnaryOp(Not(), tmp), [], []))
                        ast_stack.append(ast_stack[-1][-1].body)
                    '''
                    ast_stack[-1][-1] = If(UnaryOp(Not(),
                        BoolOp(op=Or(), values=[Name(ast_stack[-1][-2].value),
                            BoolOp(op=And(), values=[Name(ast_stack[-1][-1].test.id), ast_stack[-1][-1].body[0].value])])))
                    ast_stack.append(ast_stack[-1][-1].body)
                    ast_stack[-2].pop(-2)
                    '''
            else:
                tmp = get_slot_name(cmd_data[1])
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
                tmp = get_slot_name(cmd_data[2])
                ast_stack[-1].append(If(tmp, [], []))
            ast_stack[-1][-1].body.append(Expr(Call(Name(id=db_data["name"]), [Constant(cmd_data[0])], [])))
        # 19 is ifSlotSendTolabel
        elif current_cmd == 19:
            if cmd_data[2] == 0:
                tmp = lastExpr.value
                ast_stack[-1].append(If(UnaryOp(Not(), tmp), [], []))
                ast_stack[-1].pop(-2)
            else:
                tmp = get_slot_name(cmd_data[2])
                ast_stack[-1].append(If(UnaryOp(Not(), tmp), [], []))
            ast_stack[-1][-1].body.append(Expr(Call(Name(id=db_data["name"]), [Constant(cmd_data[0])], [])))
        # 35 is apply function to Object
        elif current_cmd == 36:
            ast_stack[-1].append(
                FunctionDef(db_data["name"] + "_" + str(cmd_data[0]), empty_args, [], []))
            ast_stack.append(ast_stack[-1][-1].body)
        # 40 is operation type aka comparison
        elif current_cmd == 40 and cmd_data[0] in [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]:
            if cmd_data[1] == 2:
                lval = get_slot_name(cmd_data[2])
            else:
                lval = Constant(cmd_data[2])
            if cmd_data[3] == 2:
                rval = get_slot_name(cmd_data[4])
            else:
                rval = Constant(cmd_data[4])

            if cmd_data[0] in [4]:
                if cmd_data[0] == 4:
                    op = Mod()
                lastExpr = Expr(BinOp(lval, op, rval))
            elif cmd_data[0] in [5, 6]:
                if cmd_data[0] == 5:
                    op = And()
                if cmd_data[0] == 6:
                    op = Or()
                lastExpr = Expr(BoolOp(op, [UnaryOp(Not(), lval), UnaryOp(Not(),rval)]))
            elif cmd_data[0] in [7, 8]:
                if cmd_data[0] == 7:
                    op = And()
                if cmd_data[0] == 8:
                    op = Or()
                lastExpr = Expr(BoolOp(op, [lval, rval]))
            elif cmd_data[0] in [9, 10, 11, 12, 13]:
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
                lastExpr = Expr(Compare(lval, [op], [rval]))
            ast_stack[-1].append(lastExpr)
        # 41 is StoreValue aka SLOT assignment
        elif current_cmd == 41:
            if cmd_data[0] == 2:
                lval = get_slot_name(cmd_data[1])
            else:
                lval = Constant(cmd_data[1])
            if cmd_data[2] == 2:
                rval = get_slot_name(cmd_data[3])
            else:
                rval = Constant(cmd_data[3])
            tmp = Assign([lval], rval)
            ast_stack[-1].append(tmp)
        # 49 is ModifyVar_
        elif current_cmd == 49 and cmd_data[0] in [0, 1, 2, 3]:
            if cmd_data[1] == 2:
                lval = get_slot_name(cmd_data[2])
            else:
                lval = Constant(cmd_data[2])
            if cmd_data[3] == 2:
                rval = get_slot_name(cmd_data[4])
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
            if current_cmd in [39, 40, 42, 43, 44, 45, 46, 23036, 23037, 23145, 23148, 23156]:
                lastExpr = Expr(Call(Name(id=db_data["name"]), args=list(map(sanitizer(current_cmd), enumerate(cmd_data))), keywords=[]))

            if len(ast_stack) == 1:
                ast_stack.append(astor_handler)
            ast_stack[-1].append(
                Expr(Call(Name(id=db_data["name"]), args=list(map(sanitizer(current_cmd), enumerate(cmd_data))), keywords=[])))
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
