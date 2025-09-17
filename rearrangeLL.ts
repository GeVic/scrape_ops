interface ListNode {
  val: number;
  next: ListNode | null;
}

export default function rearrangeLinkedList(head: ListNode | null): void {
  let slow: ListNode | null = head;
  let fast: ListNode | null = head;
  while (fast !== null && fast.next !== null) {
    slow = slow!.next;
    fast = fast.next.next;
  }
  // reverse the second half
  let prev: ListNode | null = null;
  let curr: ListNode | null = slow;
  while (curr !== null) {
    let tmp: ListNode | null = curr.next;
    curr.next = prev;
    prev = curr;
    curr = tmp;
  }
  // merge the two halves
  let first: ListNode | null = head;
  let second: ListNode | null = prev;
  while (second !== null && second.next !== null) {
    let tmp1: ListNode | null = first!.next;
    first!.next = second;
    first = tmp1;

    let tmp2: ListNode | null = second.next;
    second.next = first;
    second = tmp2;
  }
}
