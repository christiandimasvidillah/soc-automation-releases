from intake_circuit_breaker import IntakeCircuitBreaker
b=IntakeCircuitBreaker(threshold=3,cooldown_seconds=10)
for i in range(2):assert b.failure(RuntimeError('same'),now=i)['state']=='closed'
state=b.failure(RuntimeError('same'),now=2);assert state['state']=='open' and state['consecutive_failures']==3
assert b.is_open(now=5);assert not b.is_open(now=13);assert b.snapshot(now=13)['consecutive_failures']==0
b.failure(ValueError('a'),now=20);b.failure(RuntimeError('b'),now=21);assert b.snapshot(now=21)['consecutive_failures']==1
print('PASS test_intake_circuit_breaker')
