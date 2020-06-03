import pytest

from algotradepy.subscribable import Subscribable


@pytest.fixture
def observable():
    class Observable(Subscribable):
        def __init__(self):
            super().__init__()

        def foo(self, *args, **kwargs):
            return args, kwargs

        def _bar(self, *args, **kwargs):
            return args, kwargs

    observable = Observable()
    return observable


def test_subscribe_to_public_no_target_args_requested(observable):
    res_one = None

    def callback_fn_one(*args, **kwargs):
        nonlocal res_one
        res_one = args, kwargs

    res_two = None

    def callback_fn_two(*args, **kwargs):
        nonlocal res_two
        res_two = args, kwargs

    observable.subscribe(
        target_fn=observable.foo,
        callback=callback_fn_one,
        include_target_args=False,
        callback_kwargs={"one": 1},
    )
    observable.subscribe(
        target_fn=observable.foo,
        callback=callback_fn_two,
        include_target_args=False,
        callback_kwargs={"two": 2},
    )

    observable.foo(3, three=4)

    args_, kwargs_ = res_one

    assert len(args_) == 0
    assert len(kwargs_) == 1
    assert "one" in kwargs_

    args_, kwargs_ = res_two

    assert len(args_) == 0
    assert len(kwargs_) == 1
    assert "two" in kwargs_


def test_subscribe_to_public_target_args_requested(observable):
    res = None

    def callback_fn(*args, **kwargs):
        nonlocal res
        res = args, kwargs

    observable.subscribe(
        target_fn=observable.foo,
        callback=callback_fn,
        include_target_args=True,
        callback_kwargs={"one": 1},
    )

    observable.foo(2, three=3)
    args, kwargs = res

    assert len(args) == 1
    assert 2 in args
    assert len(kwargs) == 2
    assert "one" in kwargs and "three" in kwargs


def test_unsubscribe(observable):
    res_one = None

    def callback_fn_one(*args, **kwargs):
        nonlocal res_one
        res_one = args, kwargs

    res_two = None

    def callback_fn_two(*args, **kwargs):
        nonlocal res_two
        res_two = args, kwargs

    observable.subscribe(
        target_fn=observable.foo,
        callback=callback_fn_one,
        include_target_args=False,
        callback_kwargs={"one": 1},
    )
    observable.subscribe(
        target_fn=observable.foo,
        callback=callback_fn_two,
        include_target_args=False,
        callback_kwargs={"two": 2},
    )
    observable.unsubscribe(
        target_fn=observable.foo, callback=callback_fn_two,
    )

    observable.foo(3, three=4)

    args_, kwargs_ = res_one

    assert len(args_) == 0
    assert len(kwargs_) == 1
    assert "one" in kwargs_

    assert res_two is None


def test_subscribe_to_private_raises(observable):
    def callback_fn():
        pass

    with pytest.raises(AttributeError):
        observable.subscribe(
            target_fn=observable._bar, callback=callback_fn,
        )


def test_subscribe_to_Subscribable_class_method_raises(observable):
    def callback_fn():
        pass

    with pytest.raises(AttributeError):
        observable.subscribe(
            target_fn=observable.subscribe, callback=callback_fn,
        )


def test_subscribe_to_non_existant_method_raises(observable):
    def callback_fn():
        pass

    with pytest.raises(AttributeError):
        observable.subscribe(
            target_fn=observable.baz, callback=callback_fn,
        )
