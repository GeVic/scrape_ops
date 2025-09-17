interface ListNode {
  val: number;
  next: ListNode | null;
}

export default function reverseLinkedList(
  head: ListNode | null,
): ListNode | null {
  let current: ListNode | null = head;
  let prev: ListNode | null = null;

  while (current !== null) {
    let tmp: ListNode | null = current.next;
    current.next = prev;
    prev = current;
    current = tmp;
  }
  return prev;
}
