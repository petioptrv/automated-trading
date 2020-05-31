from functools import wraps
from inspect import ismethod
from typing import Callable, Optional


class Subscribable:
    """Implicitly enables Observer or Pub-Sub pattern.

    Classes inheriting from the Subscribable class can have their public methods
    subscribed to by other other objects.
    """

    def __init__(self):
        self._subscriptions = {}

    def subscribe(
        self,
        target_fn: Callable,
        callback: Callable,
        include_target_args: bool = True,
        callback_kwargs: Optional[dict] = None,
    ):
        """Subscribe to target method.

        Parameters
        ----------
        target_fn : Callable
            The method to subscribe to. Valid methods are all public methods
            of the final class, except for the public methods inherited
            from the Subscribable class.
        callback : Callable
            The function to call after the target was called.
        include_target_args : bool, default True
            Whether or not to include the positional and keyword arguments
            used call the target method when calling the callback function.
        callback_kwargs : dict, optional, default None
            Keyword arguments to pass to the callback function.
        """
        target_fn = self._validate_target(target_fn=target_fn)
        if callback_kwargs is None:
            callback_kwargs = {}
        target_fn_name = target_fn.__name__
        if target_fn_name in self._subscriptions:
            self._subscriptions[target_fn_name][callback] = (
                include_target_args,
                callback_kwargs,
            )
        else:
            self._subscriptions[target_fn_name] = {
                callback: (include_target_args, callback_kwargs),
            }

    def unsubscribe(self, target_fn: Callable, callback: Callable):
        """Unsubscribe from target method.

        Parameters
        ----------
        target_fn : Callable
            The method to unsubscribe from.
        callback : Callable
            The callback function to unsubscribe from the target method.
        """
        target_fn = self._validate_target(target_fn=target_fn)
        target_fn_name = target_fn.__name__
        if target_fn_name in self._subscriptions:
            if callback in self._subscriptions[target_fn_name]:
                del self._subscriptions[target_fn_name][callback]

    def _validate_target(self, target_fn: Callable) -> Callable:
        if ismethod(target_fn):
            target_fn = target_fn.__func__
        target_fn_name = target_fn.__name__
        if hasattr(Subscribable, target_fn_name):
            raise AttributeError(
                f"Cannot subscribe to a function of the {Subscribable} class."
                f" Attempted to subscribe to {target_fn_name}."
            )
        if target_fn_name.startswith("_"):
            raise AttributeError(
                f"Cannot subscribe to a private method ({target_fn_name})."
            )
        if not hasattr(self, target_fn_name):
            raise AttributeError(
                f"Class {self.__class__} has no method {target_fn.__name__}"
            )
        return target_fn

    def __getattribute__(self, item):
        try:
            _subscriptions = super().__getattribute__("_subscriptions")
        except AttributeError:
            _subscriptions = None
        attr = super().__getattribute__(item)

        if (
            _subscriptions is not None
            and not item.startswith("_")
            and ismethod(attr)
            and item in _subscriptions
        ):
            attr = self._wrap_attr(attr=attr)

        return attr

    def _wrap_attr(self, attr):
        attr_name = attr.__name__
        callbacks = self._subscriptions[attr_name]
        attr_fn = attr.__func__

        @wraps(attr)
        def execute_attr(*args, **kwargs):
            attr_fn(self, *args, **kwargs)
            for callback, params in callbacks.items():
                include_target_args, callback_kwargs = params
                if include_target_args:
                    callback(*args, **kwargs, **callback_kwargs)
                else:
                    callback(**callback_kwargs)

        return execute_attr
