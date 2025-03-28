import random
import os

random.seed(42)
salbp_main_dir = r"C:\Projetos\OAHF\Instances\salbp-1"
writing_dir = r"C:\Projetos\OAHF\Instances\alwabp\training_instances"

os.makedirs(writing_dir, exist_ok=True)

def listar_pastas_e_arquivos(diretorio):
    for root, dirs, files in os.walk(diretorio):
        path_parts = root.replace(diretorio, '').strip(os.sep).split(os.sep)        
        
        for file_name in files:
            file_name_no_ext = os.path.splitext(file_name)[0]
                        
            output_name = f"var_{'_'.join(path_parts)}_{file_name_no_ext}"
            input_path = os.path.join(root, file_name)
            output_path = os.path.join(writing_dir, output_name)
            generate_training_instances(input_path, output_path)

def generate_training_instances(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as file:
        content = file.read()

    try:
        task_times_text = content.split("<task times>")[1].split("<precedence relations>")[0].strip()
        precedence_text = content.split("<precedence relations>")[1].split("<end>")[0].strip()
    except IndexError:
        raise ValueError("O arquivo nao contem as secoes esperadas.")

    task_times: list[int] = []
    precedence_relations: list[tuple[int, int]] = []

    for line in task_times_text.splitlines():
        if line.strip():
            parts = line.split()
            task_id = int(parts[0])
            time = int(parts[1])
            task_times.append((task_id, time))

    task_times.sort(key=lambda x: x[0])
    task_times = [time for _, time in task_times]

    for line in precedence_text.splitlines():
        if line.strip():
            a, b = line.split(',')
            precedence_relations.append((int(a), int(b)))

    # Defina o valor de num_workers com base no output_path
    if any(substring in output_path for substring in ["large", "medium"]):
        num_workers = random.choice([10, 11])
    elif "small" in output_path:
        num_workers = random.choice([4, 5, 6, 7])
    num_tasks = len(task_times)

    def calcular_tempo(i, j, T):
        fator = random.choice([3, 4, 5])
        # Define uma chance de 20% para inviabilidade
        if random.random() < 0.2:
            return "Inf"
        else:
            return str(T * fator)

    matrix = []
    for i in range(num_tasks):
        T = task_times[i]
        linha = [calcular_tempo(i, j, T) for j in range(1, num_workers+1)]
        if all(val == "Inf" for val in linha):
            linha[0] = str(T * 3)
        matrix.append(linha)

    output_lines = []
    output_lines.append(str(num_tasks))
    for linha in matrix:
        output_lines.append(" ".join(linha))
    for a, b in precedence_relations:
        output_lines.append(f"{a} {b}")
    output_lines.append("-1 -1")

    final_output = "\n".join(output_lines)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(final_output)

    print(f"Conteudo salvo em {output_path}")


listar_pastas_e_arquivos(salbp_main_dir)