import astor_install

import os, struct, json, sys, astor
from ast import *
GAME = "BBCF"
slot_0_temp = Name("SLOT_0")

command_db_lookup = {}
slot_db_lookup = {}
named_value_lookup = {}
named_button_lookup = {}
named_direction_lookup = {}
upon_db_lookup = {}
animation_db_lookup = {}

MODE = "<"
error = False

def decode_op(node):
    if isinstance(node, UnaryOp) and isinstance(node.op, Invert):
        return 14
    elif isinstance(node, BinOp) or isinstance(node, BoolOp):
        if isinstance(node.op, Add):
            return 0
        elif isinstance(node.op, Sub):
            return 1
        elif isinstance(node.op, Mult):
            return 2
        elif isinstance(node.op, Div):
            return 3
        elif isinstance(node.op, Mod):
            return 4
        elif isinstance(node.op, And):
            return 5
        elif isinstance(node.op, Or):
            return 6
        elif isinstance(node.op, BitAnd):
            return 7
        elif isinstance(node.op, BitOr):
            return 8
    elif isinstance(node, Compare):
        if isinstance(node.ops[0], Eq):
            return 9
        elif isinstance(node.ops[0], Gt):
            return 10
        elif isinstance(node.ops[0], Lt):
            return 11
        elif isinstance(node.ops[0], GtE):
            return 12
        elif isinstance(node.ops[0], LtE):
            return 13
        elif isinstance(node.ops[0], NotEq):
            return 15
    raise Exception("Unknown op", node)

def decode_move(value):
    value.id = value.id.lower()
    tmp = named_value_lookup.get(value.id)
    if tmp is not None:
        return int(tmp)
    else:
        if value.id.replace("input_", "")[:2] == '0x':
            try:
                return int(value.id.replace("input_", ""), 16)
            except ValueError:
                pass
        buttonstr = value.id[-1]
        directionstr = value.id[:-1]
        return (int(named_button_lookup[buttonstr]) << 8) + int(
            named_direction_lookup[directionstr])

def decode_upon(s):
    s = s.lower().replace("upon_", "")
    if s in upon_db_lookup:
        return int(upon_db_lookup[s])
    else:
        return int(s)


def decode_var(node):
    if isinstance(node, UnaryOp):
        return [0, -node.operand.value]
    elif isinstance(node, Constant):
        return [0, node.value]
    elif node.id.lower().replace("slot_", "") in slot_db_lookup:
        return [2, int(slot_db_lookup[node.id.lower().replace("slot_", "")])]
    else:
        try:
            return [2, int(node.id.lower().replace("slot_", ""))]
        except ValueError:
            raise Exception("unknown SLOT " + node.id, node)


def write_command_by_name(name, params):
    cmd_data = command_db_lookup[name.lower()]
    write_command_by_id(cmd_data["id"], params)


def write_command_by_id(command, params):
    global output_buffer
    cmd_data = command_db[command]
    if command in unknown_list:
        return
    command = int(command)
    if "type_check" in cmd_data:
        type_check = cmd_data["type_check"]
        type_check.sort()
        n = len(params) + len(type_check)
        for i in range(n):
            if i in type_check:
                var = decode_var(params[i])
                params.insert(i, var[0])
                params[i+1] = var[1]
    my_params = list(params)
    for index, value in enumerate(my_params):
        if isinstance(value, str):
            pass
        elif isinstance(value, int):
            pass
        elif isinstance(value, float):
            pass
        elif isinstance(value, Constant):
            my_params[index] = value.value
        elif isinstance(value, Name):
            if command in [43, 14001, 14012]:
                my_params[index] = decode_move(value)
            elif command in [17, 29, 30, 21007]:
                my_params[index] = decode_upon(value.id)
            elif command in [9322, 9324, 9334, 9336]:
                s = value.id.lower()
                if s in animation_db_lookup:
                    my_params[index] = int(animation_db_lookup[s])
                else:
                    my_params[index] = int(s)
        elif isinstance(value, UnaryOp):
            my_params[index] = -value.operand.value
        else:
            raise Exception("Unknown type " + str(type(value)))
    if command in [11058, 22019] and len(my_params) == 1:
        new_params = []
        for attribute in "HBFPT":
            if attribute in my_params[0]:
                new_params.append(1)
            else:
                new_params.append(0)
        my_params = new_params
    output_buffer.write(struct.pack(MODE + "I", int(command)))
    for i, v1 in enumerate(my_params):
        if isinstance(v1, str):
            my_params[i] = v1.encode()
    if "format" in cmd_data:
        output_buffer.write(struct.pack(MODE + cmd_data["format"], *my_params))
    else:
        output_buffer.write(struct.pack(MODE + str(cmd_data["size"] - 4) + "s", *my_params))

def is_operation(value):
    return isinstance(value, Compare) or isinstance(value, BinOp) or isinstance(value, BoolOp) or (isinstance(value, UnaryOp) and isinstance(value.op, Invert))

class Rebuilder(astor.ExplicitNodeVisitor):

    def visit_Module(self, node):
        global output_buffer, root
        root = node
        state_count = 0
        output_buffer.write(struct.pack(MODE + "I", state_count))
        for function in node.body:
            if type(function) != FunctionDef:
                raise Exception("Root level elements must be functions", function)
            if len(function.decorator_list) == 0 or function.decorator_list[0].id.lower() != "state":
                continue
            function._index = state_count
            state_count += 1
            if function.name.startswith('__') and function.name[2].isdigit():
                function.name = function.name[2:]
            function.name.replace('__sp__', ' ').replace('__qu__', '?').replace('__at__', '@').replace('__ds__', '-' )
            bytelog = function.name.encode()
            output_buffer.write(struct.pack(MODE + "32sI", function.name.encode(), 0xFADEF00D))
        node._dataStart = output_buffer.tell()
        output_buffer.seek(0)
        output_buffer.write(struct.pack(MODE + "I", state_count))
        for child_node in node.body:
            self.visit_RootFunctionDef(child_node)

    def visit_Str(self, node):
        pass

    def visit_RootFunctionDef(self, node):
        global output_buffer, root
        output_buffer.seek(0, 2)
        if len(node.decorator_list) == 1:
            if node.decorator_list[0].id.lower() == "state":
                # Write offset into state table
                start_offset = output_buffer.tell() - root._dataStart
                output_buffer.seek(4 + 36 * node._index + 32)
                output_buffer.write(struct.pack(MODE + "I", start_offset))
                output_buffer.seek(0, 2)
                if node.name.startswith('__') and node.name[2].isdigit():
                    node.name = node.name[2:]
                node.name.replace('__sp__', ' ').replace('__qu__', '?').replace('__at__', '@').replace('__ds__', '-' )
                write_command_by_id("0", [node.name])
                self.visit_body(node.body)
                write_command_by_id("1", [])
            elif node.decorator_list[0].id.lower() == "subroutine":
                if node.name.startswith('__') and node.name[2].isdigit():
                    node.name = node.name[2:]
                node.name.replace('__sp__', ' ').replace('__qu__', '?').replace('__at__', '@').replace('__ds__', '-' )
                write_command_by_id("8", [node.name])
                self.visit_body(node.body)
                write_command_by_id("9", [])
        else:
            raise Exception("Root functions must have a decorator", node)

    def visit_Pass(self, node):
        pass

    def visit_Call(self, node):
        for index, value in enumerate(node.args):
            if isinstance(value, Call) or is_operation(value):
                self.visit_Assign(Assign([slot_0_temp], value))
                node.args[index] = slot_0_temp

        node.func.id = node.func.id.lower()
        # We have a function call. Is it a named function or is it UnknownXXXXX
        if "unknown" in node.func.id:
            cmd_id = node.func.id.replace("unknown", "")
        elif node.func.id in command_db_lookup:
            cmd_id = command_db_lookup[node.func.id]["id"]
        else:
            raise Exception("Unknown command", node)
        write_command_by_id(cmd_id, node.args)

    # Concerns def upon_ and applyFunctionToObject
    def visit_FunctionDef(self, node):
        if len(node.decorator_list) > 0 and "stateregister" in node.decorator_list[0].id.lower():
            if node.name.startswith('__') and node.name[2].isdigit():
                node.name = node.name[2:]
            node.name.replace('__sp__', ' ').replace('__qu__', '?').replace('__at__', '@').replace('__ds__', '-' )
            write_command_by_id("14001", [node.name, Name(node.args.args[0].arg)])
            self.visit_body(node.body)
            write_command_by_id("14002", [])
            return
        node.name = node.name.lower()
        if "upon" in node.name:
            write_command_by_id("15", [decode_upon(node.name)])
            self.visit_body(node.body)
            write_command_by_id("16", [])
        elif "runonobject" in node.name:
            write_command_by_id("36", [int(node.name.replace("runonobject_", ""))])
            self.visit_body(node.body)
            write_command_by_id("35", [])
        else:
            raise Exception("Prohibited inner function", node)


    def visit_If(self, node):
        find1 = False
        find2 = False

        def is_not(node_test):
            return isinstance(node_test, UnaryOp) and isinstance(node_test.op, Not)
        def is_slot(node_test):
            return isinstance(node_test, Name) or isinstance(node_test, Call) or is_operation(node_test)

        try:
            if command_db_lookup[node.body[0].value.func.id.lower()]["id"] == "18" or command_db_lookup[node.body[0].value.func.id.lower()]["id"] == "19":
                if is_not(node.test):
                    find2 = True
                else:
                    find1 = True
        except Exception:
            pass
        if find1 and is_slot(node.test):
            if isinstance(node.test, Name):
                write_command_by_id("18", [node.body[0].value.args[0], node.test])
            else:
                self.visit(node.test)
                write_command_by_id("18", [node.body[0].value.args[0], slot_0_temp])
                if len(node.orelse) > 0:
                    raise Exception("This is not a real if: else nodes don't work here")
        elif find2 and is_not(node.test) and is_slot(node.test.operand):
            if isinstance(node.test.operand, Name):
                write_command_by_id("19", [node.body[0].value.args[0], node.test.operand])
            else:
                self.visit(node.test.operand)
                write_command_by_id("19", [node.body[0].value.args[0], slot_0_temp])
                if len(node.orelse) > 0:
                    raise Exception("This is not a real if: else nodes don't work here")
        elif is_slot(node.test):
            if isinstance(node.test, Name):
                write_command_by_id("4", [node.test])
            else:
                self.visit(node.test)
                write_command_by_id("4", [slot_0_temp])
            self.visit_body(node.body)
            write_command_by_id("5", [])
        elif is_not(node.test) and is_slot(node.test.operand):
            if isinstance(node.test.operand, Name):
                write_command_by_id("54", [node.test.operand])
            else:
                self.visit(node.test.operand)
                write_command_by_id("54", [slot_0_temp])
            self.visit_body(node.body)
            write_command_by_id("55", [])
        else:
            raise Exception("Unhandled if")
        if len(node.orelse) > 0:
            write_command_by_id("56", [])
            self.visit_body(node.orelse)
            write_command_by_id("57", [])

    def visit_UnaryOp(self, node):
        return

    def visit_BoolOp(self, node):
        for i, v in enumerate(node.values):
            if isinstance(v, Call) or is_operation(v):
                self.visit_Assign(Assign([slot_0_temp], v))
                node.values[i] = slot_0_temp
        self.visit_Assign(Assign([slot_0_temp], node))

    def visit_BinOp(self, node):
        v = node.left
        if isinstance(v, Call) or is_operation(v):
            self.visit_Assign(Assign([slot_0_temp], v))
            node.left = slot_0_temp
        v = node.right
        if isinstance(v, Call) or is_operation(v):
            self.visit_Assign(Assign([slot_0_temp], v))
            node.right = slot_0_temp
        self.visit_Assign(Assign([slot_0_temp], node))

    def visit_Compare(self, node):
        v = node.left
        if isinstance(v, Call) or is_operation(v):
            self.visit_Assign(Assign([slot_0_temp], v))
            node.left = slot_0_temp
        v = node.comparators[0]
        if isinstance(v, Call) or is_operation(v):
            self.visit_Assign(Assign([slot_0_temp], v))
            node.comparators[0] = slot_0_temp
        self.visit_Assign(Assign([slot_0_temp], node))

    def visit_Assign(self, node):
        aval = node.targets[0]
        if isinstance(node.value, Call):
            self.visit(node.value)
            if aval.id.lower() != "slot_0":
                node.value = slot_0_temp
                self.visit(node)
        elif isinstance(node.value, Name) or isinstance(node.value, Constant) or (isinstance(node.value, UnaryOp) and (isinstance(node.value.operand, Name) or isinstance(node.value.operand, Constant))) :
            # StoreValue
            write_command_by_id("41", [node.targets[0], node.value])
        else:
            op_id = [decode_op(node.value)]
            if isinstance(node.value, BinOp):
                lval = node.value.left
                rval = node.value.right
            elif isinstance(node.value, BoolOp):
                lval = node.value.values[0]
                rval = node.value.values[1]
            elif isinstance(node.value, Compare):
                lval = node.value.left
                rval = node.value.comparators[0]
            elif isinstance(node.value, UnaryOp) and isinstance(node.value.op, Invert):
                lval = node.value.operand.left
                rval = node.value.operand.right
            else:
                raise Exception("How did this happen")
            if isinstance(lval, Call) or is_operation(lval):
                self.visit(Assign([slot_0_temp], lval))
                lval = slot_0_temp
            if isinstance(rval, Call) or is_operation(rval):
                self.visit(Assign([slot_0_temp], rval))
                rval = slot_0_temp
            if isinstance(aval, Name) and isinstance(lval, Name) and aval.id.lower() == lval.id.lower():
                # ModifyVar
                write_command_by_id("49", op_id + [aval, rval])
            elif aval.id.lower() == "slot_0":
                # op
                write_command_by_id("40", op_id + [lval, rval])
            else:
                # Unknown47 / PrivateFunction
                write_command_by_id("47", op_id + [aval, lval, rval])

    def visit_body(self, nodebody):
        global output_buffer, error
        for childNode in nodebody:
            self.visit(childNode)

    def visit_Expr(self, node):
        self.visit(node.value)

    def generic_visit(self, node):
        print(type(node).__name__)


def rebuild_bbscript(filename, output_path):
    global output_buffer
    output_name = os.path.join(output_path, os.path.split(filename)[1].split('.')[0] + "_error.bin")
    source_ast = astor.code_to_ast.parse_file(filename)
    output_buffer = open(output_name, "wb")
    try:
        Rebuilder().visit(source_ast)
    except Exception as e:
        if len(e.args) > 1:
            print("\033[91m", e.args[0], "\n", astor.to_source(e.args[1]), "at line ", e.args[1].lineno, "\033[0m", sep="")
        else:
            print("\033[91m", e, "\033[0m", sep="")

        if debug:
            output_buffer.close()
            os.replace(output_name, output_name.replace("_error.", "."))
        sys.exit(0)
    output_buffer.close()
    os.replace(output_name, output_name.replace("_error.", "."))


if __name__ == '__main__':
    flag_list = "Flags: --debug, --remove"
    debug = remove_unknown = False
    unknown_list = []
    input_file = None
    output_path = None

    for i, v in enumerate(sys.argv[1:]):
        if "-h" in v:
            print("Usage:" + GAME + "_Script_Rebuilder.py scr_xx.py outdir")
            print("Default output directory if left blank is the input file's directory.")
            print(flag_list)
            print("--debug: Create a scr_xx_error.bin file upon crashing")
            print("--remove: Delete the corresponding command name/id from the .bin file (THIS CAN BREAK FILES!!!)")
            sys.exit(0)
        if "--" in v:
            if "--debug" == v:
                debug = True
            elif "--remove" == v:
                remove_unknown = True
            else:
                raise Exception("Flag doesn't exist")
            continue
        if (sys.argv[i] == "--remove" or sys.argv[i][-1] == ",") and remove_unknown:
            unknown_list += v.split(",")
        elif input_file is None:
            input_file = v
        elif output_path is None:
            output_path = v

    if not input_file or input_file.split(".")[-1] != "py":
        print("Usage:" + GAME + "_Script_Rebuilder.py scr_xx.py outdir")
        print("Default output directory if left blank is the input file's directory.")
        print(flag_list)
        sys.exit(1)

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
    character_name = os.path.split(input_file)[-1].replace("scr_", "").split(".")[0]
    if character_name[-2:] == "ea" and len(character_name) > 2:
        character_name = character_name[:-2]
    try:
        upon_db.update(json.loads(open(os.path.join(pypath, "static_db/" + GAME + "/upon_db/" + character_name + ".json")).read()))
    except IOError:
        pass
    try:
        slot_db.update(json.loads(open(os.path.join(pypath, "static_db/" + GAME + "/slot_db/" + character_name + ".json")).read()))
    except IOError:
        pass

    for k, v in command_db.items():
        v["id"] = k
        if "name" in v:
            v["name"] = v["name"].lower()
            command_db_lookup[v["name"]] = v
        else:
            command_db_lookup["unknown" + k] = v
    slot_db_lookup = {v.lower(): k for k, v in slot_db.items()}
    for k, v in move_inputs.items():
        named_value_lookup[v.lower()] = k
    for k, v in normal_inputs['grouped_values'].items():
        named_value_lookup[v.lower()] = k
    for k, v in normal_inputs['button_byte'].items():
        named_button_lookup[v.lower()] = k
    for k, v in normal_inputs['direction_byte'].items():
        named_direction_lookup[v.lower()] = k
    upon_db_lookup = {v.lower(): k for k, v in upon_db.items()}
    animation_db_lookup = {v.lower(): k for k, v in animation_db.items()}

    if remove_unknown:
        unknown_list = list(filter(None, unknown_list))
        for i, v in enumerate(unknown_list):
            if v in command_db:
                continue
            try:
                unknown_list[i] = command_db_lookup[v.lower()]['id']
            except KeyError:
                print("Unknown command '" + v + "'")
                sys.exit(1)

    if output_path is None:
        rebuild_bbscript(input_file, os.path.split(input_file)[0])
    else:
        rebuild_bbscript(input_file, output_path)
    print("\033[96m" + "complete" + "\033[0m")
