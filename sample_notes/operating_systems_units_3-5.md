# Operating Systems - Unit 3: Deadlocks

A deadlock is a situation where a set of processes are blocked because each process is holding a resource and waiting for another resource held by some other process.

## Necessary conditions for deadlock (Coffman conditions)
1. Mutual exclusion: at least one resource must be held in a non-sharable mode.
2. Hold and wait: a process holding at least one resource is waiting to acquire additional resources held by other processes.
3. No preemption: a resource can be released only voluntarily by the process holding it.
4. Circular wait: there exists a set of waiting processes P0, P1, ..., Pn such that P0 waits for P1, P1 waits for P2, and Pn waits for P0.

## Deadlock prevention
Prevention works by ensuring that at least one of the four necessary conditions can never hold. For circular wait, impose a total ordering of resource types and require that each process requests resources in increasing order.

## Banker's algorithm
The Banker's algorithm is a deadlock avoidance algorithm. It keeps the system in a safe state: a state in which there exists a sequence of all processes such that each can finish with the resources currently available plus those held by earlier processes in the sequence. Data structures: Available, Max, Allocation, Need = Max - Allocation.

# Unit 4: CPU Scheduling

Round Robin scheduling assigns each process a fixed time quantum in a cyclic order. If the quantum is too large it degenerates into FCFS; if too small, context switch overhead dominates.

Shortest Job First (SJF) gives the minimum average waiting time for a given set of processes, but it needs the next CPU burst length, which can only be estimated using exponential averaging of previous bursts.

Priority scheduling can cause starvation of low priority processes. Aging solves this by gradually increasing the priority of processes that wait a long time.

# Unit 5: Memory Management

Paging divides physical memory into fixed-size frames and logical memory into pages of the same size. A page table maps each page number to a frame number. The Translation Lookaside Buffer (TLB) caches recent page table entries to speed up address translation.

Thrashing happens when a process spends more time paging than executing, because it does not have enough frames for its working set.
