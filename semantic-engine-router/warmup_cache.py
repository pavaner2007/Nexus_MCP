from app.demo.benchmark_store import get_token_benchmark, get_accuracy_benchmark

t = get_token_benchmark()
print(f"tokens: {t['percent_reduction']}% reduction, generated_at={t['generated_at']}")

a = get_accuracy_benchmark()
print(f"accuracy: {a['overall_accuracy']}%, generated_at={a['generated_at']}")
