import matplotlib.pyplot as plt


def generate_cost_graph(
        total_paper_costs, total_logistics_costs,
        total_operations_costs, total_license_costs):
    # Данные для графика
    categories = ['Бумага', 'Логистика', 'Операции', 'Лицензия']
    costs = [
        total_paper_costs, total_logistics_costs,
        total_operations_costs, total_license_costs
        ]

    # Создание графика
    plt.figure(figsize=(10, 6))
    plt.bar(categories, costs, color=['blue', 'green', 'red', 'purple'])
    plt.xlabel('Категории расходов')
    plt.ylabel('Стоимость (руб.)')
    plt.title('Расходы на бумажный КДП и лицензия КЭДО')
    plt.grid(True)

    # Сохранение графика в файл
    graph_path = 'cost_graph.png'
    plt.savefig(graph_path)
    plt.close()

    return graph_path
