from src.simple_redis_cache.key_generator import clean_args, gen_cache_key


class TestCleanArgs:
    def test_clean_args_no_args(self):
        def test_func():
            pass

        result = clean_args((), test_func)
        assert result == ()

    def test_clean_args_no_self(self):
        def test_func(x: int, y: int) -> int:
            return x + y

        result = clean_args((1, 2), test_func)
        assert result == (1, 2)

    def test_clean_args_with_self(self):
        class TestClass:
            def method(self, x: int) -> int:
                return x * 2

        obj = TestClass()
        result = clean_args((obj, 5), TestClass.method)
        assert result == (5,)

    def test_clean_args_with_cls(self):
        class TestClass:
            @classmethod
            def class_method(cls, x: int) -> int:
                return x * 2

        result = clean_args((5,), TestClass.class_method)
        assert result == (5,)

    def test_clean_args_with_static_method(self):
        class TestClass:
            @staticmethod
            def static_method(x: int) -> int:
                return x * 2

        result = clean_args((5,), TestClass.static_method)
        assert result == (5,)

    def test_clean_args_multiple_args(self):
        def test_func(a: int, b: int, c: int) -> int:
            return a + b + c

        result = clean_args((1, 2, 3), test_func)
        assert result == (1, 2, 3)

    def test_clean_args_empty_tuple(self):
        def test_func(x: int) -> int:
            return x

        result = clean_args((), test_func)
        assert result == ()


class TestGenCacheKey:
    def test_gen_key_without_args(self):
        def test_func() -> int:
            return 42

        key = gen_cache_key(test_func, (), {})
        assert key.startswith("cache:")
        assert len(key) > 10

    def test_gen_key_with_positional_args(self):
        def test_func(a: int, b: int) -> int:
            return a + b

        key1 = gen_cache_key(test_func, (1, 2), {})
        key2 = gen_cache_key(test_func, (3, 4), {})
        assert key1 != key2
        assert key1.startswith("cache:")
        assert key2.startswith("cache:")

    def test_gen_key_with_kwargs(self):
        def test_func(a: int, b: int) -> int:
            return a + b

        key1 = gen_cache_key(test_func, (), {"a": 1, "b": 2})
        key2 = gen_cache_key(test_func, (), {"a": 3, "b": 4})
        assert key1 != key2

    def test_gen_key_with_mixed_args(self):
        def test_func(a: int, b: int, c: int = 0) -> int:
            return a + b + c

        key1 = gen_cache_key(test_func, (1, 2), {"c": 3})
        key2 = gen_cache_key(test_func, (1, 2), {"c": 4})
        assert key1 != key2

    def test_gen_key_with_prefix(self):
        def test_func(x: int) -> int:
            return x * 2

        key = gen_cache_key(test_func, (5,), {}, prefix="test")
        assert key.startswith("cache:test:")
        assert len(key) > 10

    def test_gen_key_without_prefix(self):
        def test_func(x: int) -> int:
            return x * 2

        key = gen_cache_key(test_func, (5,), {})
        assert key.startswith("cache:")
        assert "test" not in key

    def test_gen_key_consistency(self):
        def test_func(x: int) -> int:
            return x * 2

        key1 = gen_cache_key(test_func, (5,), {})
        key2 = gen_cache_key(test_func, (5,), {})
        assert key1 == key2

    def test_gen_key_different_functions(self):
        def func1(x: int) -> int:
            return x * 2

        def func2(x: int) -> int:
            return x * 3

        key1 = gen_cache_key(func1, (5,), {})
        key2 = gen_cache_key(func2, (5,), {})
        assert key1 != key2

    def test_gen_key_with_self(self):
        class TestClass:
            def method(self, x: int) -> int:
                return x * 2

        obj = TestClass()
        method = obj.method

        key = gen_cache_key(method, (5,), {})
        assert key.startswith("cache:")

    def test_gen_key_with_str_arg(self):
        def test_func(name: str) -> str:
            return f"Hello, {name}"

        key1 = gen_cache_key(test_func, ("Alice",), {})
        key2 = gen_cache_key(test_func, ("Bob",), {})
        assert key1 != key2

    def test_gen_key_with_bool_arg(self):
        def test_func(flag: bool) -> bool:
            return flag

        key1 = gen_cache_key(test_func, (True,), {})
        key2 = gen_cache_key(test_func, (False,), {})
        assert key1 != key2

    def test_gen_key_with_none_arg(self):
        def test_func(value: int | None) -> int | None:
            return value

        key1 = gen_cache_key(test_func, (None,), {})
        key2 = gen_cache_key(test_func, (5,), {})
        assert key1 != key2
