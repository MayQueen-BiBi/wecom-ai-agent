"""
功能开关（A/B、渐进发布）。业务代码按需读取，默认不改变现有行为。

与 ``app/workflows/dental/workflow.WORKFLOW_VERSION``、
``app/routing/policy_engine.POLICY_VERSION`` 配合做版本对比与回放。
"""

ENABLE_NEW_ROUTING = True
ENABLE_NEW_RETRIEVAL = True
