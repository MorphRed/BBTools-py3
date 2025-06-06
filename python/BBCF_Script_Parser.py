import astor_check

import os, struct, json, sys, astor
from ast import *

GAME = "BBCF"
AFFECT_SLOT_0 = [39, 40, 42, 43, 44, 45, 46, 59, 60, 61, 63, 66, 69, 70, 1116, 2065, 23036, 23037, 23045, 23145, 23146,
                 23148, 23156, 23166, 23177, 30042]
ast_root = Module([], [])
ast_stack = [ast_root.body]
slot_0_expr = None
MODE = "<"


def load_json(path_from_static):
    try:
        return json.loads(
            open(os.path.join(os.path.dirname(sys.argv[0]), "static_db/" + GAME + "/" + path_from_static)).read())
    except (IOError, json.decoder.JSONDecodeError):
        return {}


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
        op = BitAnd()
    elif operation_id == 8:
        op = BitOr()
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
    elif operation_id == 14:
        op = BitAnd()
    elif operation_id == 15:
        op = NotEq()
    else:
        raise Exception("Invalid operation_id " + str(operation_id))

    return op


def slot_handler(command, cmd_data):
    str_command = str(command)
    tmp = []
    for i, v in enumerate(cmd_data):
        if i in command_db[str_command]['type_check']:
            continue
        elif i - 1 in command_db[str_command]['type_check']:
            if cmd_data[i - 1] == 0:
                tmp.append(Constant(v))
            else:
                if no_0_command and cmd_data[i] == 0 and int(command) not in [40, 41, 47, 49]:
                    tmp.append(abstract_slot_0())
                else:
                    tmp.append(get_slot_name(v))
        else:
            tmp.append(Constant(v))

    return tmp


def abstract_slot_0():
    if len(ast_stack[-1]) > 0 and ast_stack[-1][-1] == slot_0_expr and no_0:
        ast_stack[-1].pop()
        return slot_0_expr.value
    else:
        return get_slot_name(0)


def get_input_name(command, cmd_data):
    str_cmd_data = str(cmd_data)
    # For specials
    if command in [43, 14012]:
        if "hex" in move_inputs_db and move_inputs_db["hex"]:
            if hex(cmd_data) in move_inputs_db:
                return move_inputs_db[hex(cmd_data)]
        else:
            if str_cmd_data in move_inputs_db:
                return move_inputs_db[str_cmd_data]
    # For normals
    elif command == 14001:
        if str_cmd_data in normal_inputs_db['grouped_values']:
            return normal_inputs_db['grouped_values'][str_cmd_data]
        s = struct.pack('>H', cmd_data)
        button_byte, dir_byte = struct.unpack('>BB', s)
        if str(button_byte) in normal_inputs_db['button_byte'] and str(dir_byte) in normal_inputs_db['direction_byte']:
            return normal_inputs_db['direction_byte'][str(dir_byte)] + normal_inputs_db['button_byte'][str(button_byte)]
    if "hex" in command_db[str(command)] and command_db[str(command)]['hex']:
        motion = hex(cmd_data)
    else:
        motion = str_cmd_data
    return "INPUT_" + motion


def get_animation_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in animation_db:
        return Name(animation_db[str_cmd_data])
    return Constant(cmd_data)


def get_move_condition(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in move_condition_db:
        return Name(move_condition_db[str_cmd_data])
    return Constant(cmd_data)


def get_upon_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in upon_db:
        str_cmd_data = upon_db[str_cmd_data]
    return Name("upon_" + str_cmd_data)


def get_slot_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in slot_db:
        str_cmd_data = slot_db[str_cmd_data]
    return Name("SLOT_" + str_cmd_data)


# Not used yet
def get_object_name(cmd_data):
    str_cmd_data = str(cmd_data)
    if str_cmd_data in object_db:
        return Name(object_db[str_cmd_data])
    return Constant(cmd_data)


# Changes numbers to their db value
def sanitizer(command):
    def sanitize(values):
        i = values[0]
        value = values[1]
        if raw:
            pass
        elif isinstance(value, expr):
            pass
        elif command in [43, 14001, 14012] and isinstance(value, int):
            value = Name(get_input_name(command, value))
        elif command in [17, 28, 29, 30, 31] and i == 0:
            value = get_upon_name(value)
        elif command in [21007] and i == 1:
            value = get_upon_name(value)
        elif command in [9322, 9324, 9334, 9336]:
            value = get_animation_name(value)
        elif command in [14003]:
            value = get_move_condition(value)
        else:
            value = Constant(value)
        if "hex" in command_db[str(command)] and command_db[str(command)]["hex"] and (
                isinstance(value, Constant) and isinstance(value.value, int)):
            if command_db[str(command)]["hex"] == True or i in command_db[str(command)]["hex"]:
                if isinstance(value, int):
                    value = Name(hex(value))
                else:
                    value = Name(hex(value.value))
            else:
                if isinstance(value, int):
                    value = Constant(value)
        return value

    return sanitize


def function_clean(command):
    command = command.replace("-", "__ds__").replace("@", "__at__").replace("?", "__qu__").replace(" ", "__sp__")
    if command[0].isdigit():
        command = "__" + command
    return command


def parse_bbscript_routine(file):
    global slot_0_expr, debug
    empty_args = arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[])
    astor_handler = []
    file.seek(0, os.SEEK_END)
    end = file.tell()
    file.seek(0)
    FUNCTION_COUNT, = struct.unpack(MODE + "I", file.read(4))
    file.seek(4 + 0x24 * FUNCTION_COUNT)
    # Going through the bin
    while file.tell() != end:
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
                    new_v = ''
                    for j in v:
                        new_v += chr(j)
                    cmd_data[i] = new_v
        if raw and current_cmd not in [0, 1, 8, 9]:
            command = Expr(Call(Name(id=db_data["name"]), args=list(map(sanitizer(current_cmd), enumerate(cmd_data))),
                                keywords=[]))
            ast_stack[-1].append(command)
            continue
        # AST STUFF
        # 0 is startState
        if current_cmd == 0:
            if len(ast_stack) > 1:
                ast_stack.pop()
            command = FunctionDef(function_clean(cmd_data[0]), empty_args, [], [Name(id="State")])
            ast_stack[-1].append(command)
            ast_stack.append(ast_stack[-1][-1].body)
        # 8 is startSubroutine
        elif current_cmd == 8:
            if len(ast_stack) > 1:
                ast_stack.pop()
            command = FunctionDef(function_clean(cmd_data[0]), empty_args, [], [Name(id="Subroutine")])
            ast_stack[-1].append(command)
            ast_stack.append(ast_stack[-1][-1].body)
        # 15 is upon
        elif current_cmd == 15:
            command = FunctionDef(get_upon_name(cmd_data[0]).id, empty_args, [], [])
            ast_stack[-1].append(command)
            ast_stack.append(ast_stack[-1][-1].body)
        # 14001 is Move_Register/StateRegister
        elif current_cmd == 14001:
            command = FunctionDef(function_clean(cmd_data[0]),
                                  arguments(args=[arg(get_input_name(current_cmd, cmd_data[1]))]), [],
                                  [Name(id="StateRegister")])
            ast_stack[-1].append(command)
            ast_stack.append(ast_stack[-1][-1].body)
        # 4 is if, 54 is ifNot
        elif current_cmd in [4, 54]:
            cmd_data = slot_handler(current_cmd, cmd_data)
            condition = cmd_data[0]
            if isinstance(condition, Name) and condition.id == "SLOT_0":
                condition = abstract_slot_0()
            if current_cmd == 4:
                command = If(condition, [], [])
            elif current_cmd == 54:
                command = If(UnaryOp(Not(), condition), [], [])
            ast_stack[-1].append(command)
            ast_stack.append(ast_stack[-1][-1].body)
        # 56 is else
        elif current_cmd == 56:
            ifnode = ast_stack[-1][-1]
            try:
                ast_stack.append(ifnode.orelse)
            except Exception as _:
                # When arcsys puts a random else bracket in the code that does nothing :)
                ast_stack.append([])
        # 36 is apply function to Object
        elif current_cmd == 36:
            ast_stack[-1].append(
                FunctionDef(db_data["name"] + "_" + str(cmd_data[0]), empty_args, [], []))
            ast_stack.append(ast_stack[-1][-1].body)
        # 40 is operation stored in SLOT_0, 47 is operation stored in value given, 49 is ModifyVar_
        elif current_cmd in [40, 47, 49]:
            cmd_data = slot_handler(current_cmd, cmd_data)
            cmd_data[0] = cmd_data[0].value
            if current_cmd == 40:
                aval = get_slot_name(0)
                lval = cmd_data[1]
                rval = cmd_data[2]
            elif current_cmd == 47:
                lval = cmd_data[1]
                rval = cmd_data[2]
                aval = cmd_data[3]
            elif current_cmd == 49:
                lval = cmd_data[1]
                rval = cmd_data[2]
                aval = lval
            else:
                raise Exception("Unknown command in operation")
            if isinstance(lval, Name) and lval.id == "SLOT_0":
                lval = abstract_slot_0()
            if isinstance(rval, Name) and rval.id == "SLOT_0":
                rval = abstract_slot_0()
            op = get_operation(cmd_data[0])
            if cmd_data[0] in [0, 1, 2, 3]:
                tmp = BinOp(lval, op, rval)
            elif cmd_data[0] in [4]:
                tmp = BinOp(lval, op, rval)
            elif cmd_data[0] in [5, 6, 7, 8]:
                tmp = BoolOp(op, [lval, rval])
            elif cmd_data[0] in [9, 10, 11, 12, 13, 15]:
                tmp = Compare(lval, [op], [rval])
            elif cmd_data[0] in [14]:
                tmp = UnaryOp(Invert(), BinOp(lval, op, rval))
            else:
                raise Exception("Unhandled operation")
            if isinstance(aval, Constant):
                command = Expr(
                    Call(Name(id=db_data["name"]), args=list(map(sanitizer(current_cmd), enumerate(cmd_data))),
                         keywords=[]))
            else:
                command = Assign([aval], tmp)
            if isinstance(aval, Name) and aval.id == "SLOT_0":
                slot_0_expr = command
            ast_stack[-1].append(command)
        # 41 is StoreValue, assigning to SLOT_XX
        elif current_cmd == 41:
            cmd_data = slot_handler(current_cmd, cmd_data)
            lval = cmd_data[0]
            rval = cmd_data[1]
            if isinstance(rval, Name) and rval.id == "SLOT_0":
                rval = abstract_slot_0()
            command = Assign([lval], rval)
            if isinstance(lval, Name) and lval.id == "SLOT_0":
                slot_0_expr = command
            ast_stack[-1].append(command)
        elif enable_attributes and current_cmd in [11058, 22019]:
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
        elif current_cmd in [1, 5, 9, 16, 35, 55, 57, 14002]:
            if len(ast_stack[-1]) == 0:
                ast_stack[-1].append(Pass())
            if len(ast_stack) > 1:
                astor_handler = ast_stack.pop()
            else:
                command = Expr(
                    Call(Name(id=db_data["name"]), args=list(map(sanitizer(current_cmd), enumerate(cmd_data))),
                         keywords=[]))
                ast_stack[-1][-1].body.append(command)

            # Flag stuff
            if debug and current_cmd in [1, 9]:
                debug_file.write(astor.to_source(ast_stack[-1][-1]) + "\n\n")

        else:
            if 'type_check' in command_db[str(current_cmd)]:
                cmd_data = slot_handler(current_cmd, cmd_data)
            command = Expr(Call(Name(id=db_data["name"]), args=list(map(sanitizer(current_cmd), enumerate(cmd_data))),
                                keywords=[]))
            # Things that affect slot_0
            if current_cmd in AFFECT_SLOT_0:
                slot_0_expr = Assign([get_slot_name(0)], command.value)
                command = slot_0_expr

            if len(ast_stack) == 1:
                ast_stack.append(astor_handler)
            ast_stack[-1].append(command)

    return ast_root


def parse_bbscript(filename, output_path):
    global debug_file
    file = open(filename, 'rb')
    if debug:
        debug_file = open(os.path.join(output_path, os.path.split(filename)[1].split('.')[0] + "_error.py"), "w",
                          encoding="utf-8")
    ast_root = parse_bbscript_routine(file)
    output = os.path.join(output_path, os.path.split(filename)[1].split('.')[0] + ".py")
    py = open(output, "w", encoding="utf-8")
    py.write(astor.to_source(ast_root))
    if debug:
        os.remove(os.path.join(output_path, os.path.split(filename)[1].split('.')[0] + "_error.py"))
    py.close()


if __name__ == '__main__':
    flag_list = "Flags: -h, --no-upon, --no-slot, --no-animation, --no-0, --no-0-command, --attributes, --raw, --debug"
    no_upon = no_slot = no_0 = no_0_command = debug = raw = enable_attributes = no_animation = False
    input_file = None
    output_path = None
    for v in sys.argv[1:]:
        if "-h" in v:
            print("Usage:" + GAME + "_Script_Parser.py scr_xx.bin outdir")
            print("Default output directory if left blank is the input file's directory.")
            print(flag_list)
            print("--no-upon: Disable aliasing of upons")
            print("--no-slot: Disable aliasing of slots")
            print("--no-animation: Disable aliasing of hit animations")
            print("--no-0: Delete most instances of SLOT_0 by merging them with commands assigning to SLOT_0")
            print("--no-0-command: Also merge SLOT_0 used inside of commands")
            print(
                "--attributes: Enable the abstraction of commands using attack attributes e.g. SpecificInvincibility('H')")
            print("--raw: Remove all abstraction except states and subroutines, !!!Rebuilding not supported!!! but might work")
            print("--debug: Create a scr_xx_error.py file upon crashing, file is generated state/subroutine by state/subroutine instead of all at once")
            sys.exit(0)
        if "--" in v:
            if "--no-upon" == v:
                no_upon = True
            elif "--no-slot" == v:
                no_slot = True
            elif "--no-animation" == v:
                no_animation = True
            elif "--no-0" == v:
                no_0 = True
            elif "--no-0-command" == v:
                no_0 = True
                no_0_command = True
            elif "--debug" == v:
                debug = True
            elif "--raw" == v:
                raw = True
            elif "--attributes" == v:
                enable_attributes = True
            else:
                print("Flag " + '"' + v + '"' + " doesn't exist")
                print(flag_list)
                sys.exit(1)
            continue
        if input_file is None:
            input_file = v
        elif output_path is None:
            output_path = v

    if not input_file or input_file.split(".")[-1] != "bin":
        print("Usage:" + GAME + "_Script_Parser.py scr_xx.bin outdir")
        print("Default output directory if left blank is the input file's directory.")
        print(flag_list)
        sys.exit(1)

    command_db = load_json("command_db.json")
    move_inputs_db = load_json("named_values/move_inputs.json")
    normal_inputs_db = load_json("named_values/normal_inputs.json")
    animation_db = load_json("named_values/hit_animation.json")
    move_condition_db = load_json("named_values/move_condition.json")    
    object_db = load_json("named_values/object.json")
    upon_db = load_json("upon_db/global.json")
    slot_db = load_json("slot_db/global.json")

    #Checking for a custom slot/upon db
    character_name = os.path.split(input_file)[-1].replace("scr_", "").split(".")[0]
    if character_name[-2:] == "ea" and len(character_name) > 2:
        character_name = character_name[:-2]
    upon_db.update(load_json("upon_db/" + character_name + ".json"))
    slot_db.update(load_json("slot_db/" + character_name + ".json"))

    if no_slot:
        slot_db = {}
    if no_upon:
        upon_db = {}
    if no_animation:
        animation_db = {}
    if output_path is None:
        parse_bbscript(input_file, os.path.split(input_file)[0])
    else:
        parse_bbscript(input_file, output_path)
    print("\033[96m" + "complete" + "\033[0m")
