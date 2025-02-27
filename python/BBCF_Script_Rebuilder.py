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
#Checking for a custom slot/upon db
character_name = sys.argv[1].replace("scr_", "").split(".")[0]
if character_name[:-2] == "ea":
    character_name = character_name[:-2]
try:
    upon_db.update(json.loads(open(os.path.join(pypath, "static_db/" + GAME + "/upon_db/" + character_name + ".json")).read()))
except IOError:
    pass
try:
    slot_db.update(json.loads(open(os.path.join(pypath, "static_db/" + GAME + "/slot_db/" + character_name + ".json")).read()))
except IOError:
    pass

command_db_lookup = {}
slot_db_lookup = {}
named_value_lookup = {}
named_button_lookup = {}
named_direction_lookup = {}
upon_db_lookup = {}
animation_db_lookup = {}

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

MODE = "<"
error = False

def decode_op(node):
    if isinstance(node, BinOp) or isinstance(node, BoolOp):
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
    raise Exception("UNKNOWN OP")

def decode_move(value):
    tmp = named_value_lookup.get(value.id.lower())
    if tmp is not None:
        return int(tmp)
    else:
        buttonstr = value.id[-1].lower()
        directionstr = value.id[:-1].lower()
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
            raise Exception("unknown SLOT " + node.id)


def write_command_by_name(name, params):
    cmd_data = command_db_lookup[name.lower()]
    write_command_by_id(cmd_data["id"], params)


def write_command_by_id(id, params):
    global output_buffer
    cmd_data = command_db[id]
    id = int(id)
    if "type_check" in cmd_data:
        type_check = cmd_data["type_check"]
        type_check.sort()
        n = max(len(params) + len(type_check), type_check[-1] + 1)
        for i in range(n):
            if i in type_check:
                var = decode_var(params[i])
                params.insert(i, var[0])
                params[i+1] = var[1]
    my_params = list(params)
    for index, oValue in enumerate(my_params):
        if isinstance(oValue, str):
            pass
        elif isinstance(oValue, int):
            pass
        elif isinstance(oValue, float):
            pass
        elif isinstance(oValue, Constant):
            my_params[index] = oValue.value
        elif isinstance(oValue, Name):
            if id in [43, 14001, 14012]:
                my_params[index] = decode_move(oValue)
            elif id in [17, 29, 30, 21007]:
                my_params[index] = decode_upon(oValue.id)
            elif id in [9322, 9324, 9334, 9336]:
                s = oValue.id.lower()
                if s in animation_db_lookup:
                    my_params[index] = int(animation_db_lookup[s])
                else:
                    my_params[index] = int(s)
        elif isinstance(oValue, UnaryOp):
            my_params[index] = -oValue.operand.value
        else:
            raise Exception("unknown type " + str(type(oValue)))
    if id in [11058, 22019] and len(my_params) == 1:
        new_params = []
        for attribute in "HBFPT":
            if attribute in my_params[0]:
                new_params.append(1)
            else:
                new_params.append(0)
        my_params = new_params
    output_buffer.write(struct.pack(MODE + "I", int(id)))
    if "format" in cmd_data:
        for i, v1 in enumerate(my_params):
            if isinstance(v1, str):
                my_params[i] = v1.encode()
        output_buffer.write(struct.pack(MODE + cmd_data["format"], *my_params))
    else:
        output_buffer.write(my_params[0].encode())


class Rebuilder(astor.ExplicitNodeVisitor):
    def visit_Module(self, node):
        global output_buffer
        global root
        root = node
        state_count = 0
        output_buffer.write(struct.pack(MODE + "I", state_count))
        for function in node.body:
            if type(function) != FunctionDef:
                raise Exception("Root level elements must be functions")
            if function.decorator_list[0].id.lower() != "state":
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
                write_command_by_name("startState", [node.name])
                self.visit_body(node.body)
                write_command_by_name("endState", [])
            elif node.decorator_list[0].id.lower() == "subroutine":
                if node.name.startswith('__') and node.name[2].isdigit():
                    node.name = node.name[2:]
                node.name.replace('__sp__', ' ').replace('__qu__', '?').replace('__at__', '@').replace('__ds__', '-' )
                write_command_by_name("startSubroutine", [node.name])
                self.visit_body(node.body)
                write_command_by_name("endSubroutine", [])
        else:
            raise Exception("haven't implemented this")

    def visit_Pass(self, node):
        pass

    def visit_Call(self, node):
        node.func.id = node.func.id.lower()
        # We have a function call. Is it a named function or is it UnknownXXXXX
        if "unknown" in node.func.id:
            cmd_id = node.func.id.replace("unknown", "")
        elif node.func.id in command_db_lookup:
            cmd_id = command_db_lookup[node.func.id]["id"]
        else:
            raise Exception("unknown command " + node.func.id)
        write_command_by_id(cmd_id, node.args)

# Concerns def upon_ and applyFunctionToObject
    def visit_FunctionDef(self, node):
        if len(node.decorator_list) > 0 and "stateregister" in node.decorator_list[0].id.lower():
            if node.name.startswith('__') and node.name[2].isdigit():
                node.name = node.name[2:]
            node.name.replace('__sp__', ' ').replace('__qu__', '?').replace('__at__', '@').replace('__ds__', '-' )
            write_command_by_name("Move_Register", [node.name, node.args.defaults[0]])
            self.visit_body(node.body)
            write_command_by_name("Move_EndRegister", [])
            return
        node.name = node.name.lower()
        if "upon" in node.name:
            write_command_by_name("upon", [decode_upon(node.name)])
            self.visit_body(node.body)
            write_command_by_name("endUpon", [])
        elif "runonobject" in node.name:
            write_command_by_name("RunOnObject", [int(node.name.replace("runonobject_", ""))])
            self.visit_body(node.body)
            write_command_by_name("RunOnSelf", [])
        else:
            raise Exception("prohibited inner function")
            

    def visit_If(self, node):
        find1 = False
        find2 = False
        try:
            if node.body[0].value.func.id.lower() == "conditionalsendtolabel":
                if isinstance(node.test, UnaryOp): 
                    find2 = True
                else:
                    find1 = True
        except Exception:
            pass
        if isinstance(node.test, Name) and find1:
            write_command_by_id("18", [node.body[0].value.args[0], node.test])
        elif isinstance(node.test, UnaryOp) and isinstance(node.test.operand, Name) and find2:
            write_command_by_id("19", [node.body[0].value.args[0], node.test.operand])
        elif isinstance(node.test, Name):
            # This is if(SLOT) we need to find out slot index and write it as param of if
            write_command_by_name("if", [node.test])
            self.visit_body(node.body)
            write_command_by_name("endIf", [])
            if len(node.orelse) > 0:
                write_command_by_name("else", [])
                self.visit_body(node.orelse)
                write_command_by_name("endElse", [])
        elif isinstance(node.test, UnaryOp) and isinstance(node.test.operand, Name):
            # This is if(SLOT) we need to find out slot index and write it as param of if
            write_command_by_name("ifNot", [node.test.operand])
            self.visit_body(node.body)
            write_command_by_name("endIfNot", [])
            if len(node.orelse) > 0:
                write_command_by_name("else", [])
                self.visit_body(node.orelse)
                write_command_by_name("endElse", [])
        elif (isinstance(node.test, Call) or isinstance(node.test, Compare) or isinstance(node.test, BinOp) or isinstance(node.test, BoolOp)) and find1:
            self.visit(node.test)
            write_command_by_id("18", [node.body[0].value.args[0], 2, 0])
        elif isinstance(node.test, UnaryOp) and (
                isinstance(node.test.operand, Call) or isinstance(node.test.operand, Compare) or isinstance(node.test.operand, BinOp) or isinstance(node.test.operand, BoolOp)) and find2:
            self.visit(node.test.operand)
            write_command_by_id("19", [node.body[0].value.args[0], 2, 0])
        elif isinstance(node.test, Call) or isinstance(node.test, Compare) or isinstance(node.test, BinOp) or isinstance(node.test, BoolOp):
            self.visit(node.test)
            write_command_by_name("if", [2, 0])
            self.visit_body(node.body)
            write_command_by_name("endIf", [])
            if len(node.orelse) > 0:
                write_command_by_name("else", [])
                self.visit_body(node.orelse)
                write_command_by_name("endElse", [])
        elif isinstance(node.test, UnaryOp) and (
                isinstance(node.test.operand, Call) or isinstance(node.test.operand, Compare) or isinstance(node.test.operand, BinOp) or isinstance(node.test.operand, BoolOp)):
            self.visit(node.test.operand)
            write_command_by_name("ifNot", [2, 0])
            self.visit_body(node.body)
            write_command_by_name("endIfNot", [])
            if len(node.orelse) > 0:
                write_command_by_name("else", [])
                self.visit_body(node.orelse)
                write_command_by_name("endElse", [])
        else:
            raise Exception("UNHANDLED IF")
        
    def visit_UnaryOp(self, node):
        return
    
    def visit_Assign(self, node):
        if isinstance(node.value, Call):
            self.visit(node.value)
        else:
            if isinstance(node.value, BinOp) or isinstance(node.value, BoolOp) or isinstance(node.value, Compare):
                params = [decode_op(node.value)]
                if isinstance(node.targets[0], Name) and isinstance(node.value.left, Name) and node.targets[0].id.lower() == node.value.left.id.lower():
                    if isinstance(node.value, Compare):
                        write_command_by_name("ModifyVar_", params + [node.targets[0], node.value.comparators[0]])
                    else:
                        write_command_by_name("ModifyVar_", params + [node.targets[0], node.value.right])
                elif node.targets[0].id.lower() == "slot_0":
                    if isinstance(node.value, Compare):
                        write_command_by_name("op", params + [node.value.left, node.value.comparators[0]])
                    else:
                        write_command_by_name("op", params + [node.value.left, node.value.right])
                else:
                    if isinstance(node.value, Compare):
                        write_command_by_name("PrivateFunction", params + [node.targets[0], node.value.left, node.value.comparators[0]])
                    else:
                        write_command_by_name("PrivateFunction", params + [node.targets[0], node.value.left, node.value.right])
            else:
                write_command_by_name("StoreValue", [node.targets[0], node.value])

    def visit_body(self, nodebody):
        global output_buffer, error
        try: 
            for childNode in nodebody:
                self.visit(childNode)
        except Exception as e:
            # spaghetti pls don't kill me :3
            error = True
            print("\033[91m", e, "\n" + astor.to_source(childNode) + "\n" + astor.dump_tree(childNode) + "\033[0m", sep="")

    def visit_Expr(self, node):
        self.visit(node.value)

    def generic_visit(self, node):
        print(type(node).__name__)


def rebuild_bbscript(filename, output_path):
    global output_buffer
    output_name = os.path.join(output_path, os.path.split(filename)[1].split('.')[0] + "_error.bin")
    source_ast = astor.code_to_ast.parse_file(filename)
    output_buffer = open(output_name, "wb")
    Rebuilder().visit(source_ast)
    output_buffer.close()
    if not error:
        os.replace(output_name, output_name.replace("_error.", "."))
    else:
        os.remove(output_name)
        sys.exit(1)


if __name__ == '__main__':
    no_slot = False
    input_file = None
    output_path = None
    for v in sys.argv[1:]:
        if input_file is None:
            input_file = v
        elif output_path is None:
            output_path = v
        
    if input_file.split(".")[-1] != "py":
        print("Usage:BBCF_Script_Rebuilder.py scr_xx.py outdir")
        print("Default output directory if left blank is the input file's directory.")
        sys.exit(1)
    if output_path is None:
        rebuild_bbscript(input_file, os.path.split(input_file)[0])
    else:
        rebuild_bbscript(input_file, output_path)
    print("\033[96m" + "complete" + "\033[0m")
