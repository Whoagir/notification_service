import os


def process_directory(root_dir, output_file):
    exclude_dirs = {'.git', '.idea', 'venv', '__pycache__'}
    root_dir = os.path.abspath(root_dir)
    base_name = os.path.basename(root_dir)

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs
                   if d not in exclude_dirs and not d.startswith('.')]
        # Игнорируем скрытые файлы и файлы с расширением .log
        files = [f for f in files if not f.startswith('.') and not f.endswith('.log') and not f.endswith(
            '.log~') and f != 'all.py' and f != 'tbd.py' and f != 'output.txt' and f != 'analyze_project.py' and f != 'test_db.py' and f != 'test_redis_connect.py']

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, root_dir)
            comment_path = os.path.join(base_name, relative_path)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (UnicodeDecodeError, PermissionError):
                continue

            output_file.write(f"#{comment_path}\n")
            output_file.write(content + "\n\n")


if __name__ == "__main__":
    target_dir = input("Введите путь к директории: ").strip()

    if not os.path.isdir(target_dir):
        print("Ошибка: Указанная директория не существует!")
        exit(1)

    with open('output.txt', 'w', encoding='utf-8') as f:
        process_directory(target_dir, f)
        print("Файл output.txt успешно создан!")
